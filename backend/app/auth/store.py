import asyncio
import functools
import hashlib
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id_hash TEXT PRIMARY KEY,
    sub TEXT NOT NULL,
    oauth_sid TEXT,
    user_claims TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    access_expires_at REAL NOT NULL,
    created_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    last_revalidated_at REAL NOT NULL,
    absolute_expires_at REAL NOT NULL,
    refresh_lease_until REAL NOT NULL DEFAULT 0,
    revalidate_retry_at REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sessions_sub ON sessions (sub);
CREATE INDEX IF NOT EXISTS sessions_oauth_sid ON sessions (oauth_sid);
CREATE TABLE IF NOT EXISTS login_attempts (
    state TEXT PRIMARY KEY,
    code_verifier TEXT NOT NULL,
    nonce TEXT,
    return_to TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_jti (
    jti TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);
"""

LOGIN_ATTEMPT_TTL = 600
RETRY_BACKOFF = 5


def hash_id(session_id: str) -> str:
    """Only the SHA-256 of the cookie value is stored: a leaked database does
    not hand out usable sessions."""
    return hashlib.sha256(session_id.encode()).hexdigest()


@dataclass(frozen=True)
class Session:
    id_hash: str
    sub: str
    oauth_sid: str | None
    user_claims: dict
    access_token: str
    refresh_token: str
    access_expires_at: float
    created_at: float
    last_seen_at: float
    last_revalidated_at: float
    absolute_expires_at: float
    refresh_lease_until: float
    revalidate_retry_at: float


@dataclass(frozen=True)
class LoginAttempt:
    code_verifier: str
    nonce: str | None
    return_to: str


def _session(row: sqlite3.Row | None) -> Session | None:
    if row is None:
        return None
    data = dict(row)
    data["user_claims"] = json.loads(data["user_claims"])
    return Session(**data)


def _threaded(fn):
    """Runs a blocking store method on a worker thread, on its own connection."""

    @functools.wraps(fn)
    async def wrapper(self, *args, **kwargs):
        return await asyncio.to_thread(self._call, fn, *args, **kwargs)

    return wrapper


class SessionStore:
    """Server-side sessions in SQLite (WAL): shared by several uvicorn workers."""

    def __init__(self, path: str, idle_ttl: int, absolute_ttl: int):
        self.path = path
        self.idle_ttl = idle_ttl
        self.absolute_ttl = absolute_ttl
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _call(self, fn, *args, **kwargs):
        if not self._ready:
            self._init()
        conn = self._connect()
        try:
            return fn(self, conn, *args, **kwargs)
        finally:
            conn.close()

    def _init(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
        finally:
            conn.close()
        self._ready = True

    async def init(self) -> None:
        await asyncio.to_thread(self._init)

    # --- login attempts -------------------------------------------------

    @_threaded
    def add_login_attempt(self, conn, state, code_verifier, nonce, return_to) -> None:
        conn.execute(
            "INSERT INTO login_attempts VALUES (?, ?, ?, ?, ?)",
            (state, code_verifier, nonce, return_to, time.time() + LOGIN_ATTEMPT_TTL),
        )

    @_threaded
    def pop_login_attempt(self, conn, state) -> LoginAttempt | None:
        """Single use and atomic: a replayed state finds nothing."""
        row = conn.execute(
            "DELETE FROM login_attempts WHERE state = ? "
            "RETURNING code_verifier, nonce, return_to, expires_at",
            (state,),
        ).fetchone()
        if row is None or row["expires_at"] < time.time():
            return None
        return LoginAttempt(row["code_verifier"], row["nonce"], row["return_to"])

    # --- sessions -------------------------------------------------------

    @_threaded
    def create_session(
        self, conn, *, sub, oauth_sid, user_claims, access_token, refresh_token, access_expires_at
    ) -> str:
        session_id = secrets.token_urlsafe(32)  # fresh at every login: no fixation
        now = time.time()
        conn.execute(
            "INSERT INTO sessions (id_hash, sub, oauth_sid, user_claims, access_token, refresh_token, "
            "access_expires_at, created_at, last_seen_at, last_revalidated_at, absolute_expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hash_id(session_id), sub, oauth_sid, json.dumps(user_claims), access_token,
                refresh_token, access_expires_at, now, now, now, now + self.absolute_ttl,
            ),
        )
        return session_id

    @_threaded
    def get_session(self, conn, id_hash) -> Session | None:
        return _session(conn.execute("SELECT * FROM sessions WHERE id_hash = ?", (id_hash,)).fetchone())

    @_threaded
    def touch(self, conn, id_hash) -> None:
        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE id_hash = ?", (time.time(), id_hash))

    @_threaded
    def delete_session(self, conn, id_hash) -> None:
        conn.execute("DELETE FROM sessions WHERE id_hash = ?", (id_hash,))

    @_threaded
    def delete_for_user(self, conn, *, sid=None, subs=()) -> int:
        """Back-channel logout: by OAuth session id if there is one, else by user."""
        if sid:
            return conn.execute("DELETE FROM sessions WHERE oauth_sid = ?", (sid,)).rowcount
        subs = [s for s in subs if s]
        if not subs:
            return 0
        marks = ",".join("?" * len(subs))
        return conn.execute(f"DELETE FROM sessions WHERE sub IN ({marks})", subs).rowcount

    # --- token refresh (revalidation) -----------------------------------

    @_threaded
    def claim_refresh(self, conn, id_hash, interval, lease) -> tuple[str, Session | None]:
        """Decides, atomically across workers, who refreshes. A short lease
        (not a lock held during the network call) lets the other requests wait
        for the winner instead of blocking every writer of the database.

        Returns (status, session): "gone" | "fresh" | "busy" | "claimed"."""
        conn.execute("BEGIN IMMEDIATE")
        try:
            session = _session(conn.execute("SELECT * FROM sessions WHERE id_hash = ?", (id_hash,)).fetchone())
            now = time.time()
            if session is None:
                status = "gone"
            elif now - session.last_revalidated_at < interval or session.revalidate_retry_at > now:
                status = "fresh"
            elif session.refresh_lease_until > now:
                status = "busy"
            else:
                conn.execute(
                    "UPDATE sessions SET refresh_lease_until = ? WHERE id_hash = ?", (now + lease, id_hash)
                )
                status = "claimed"
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        return status, session

    @_threaded
    def finish_refresh(self, conn, id_hash, *, access_token, refresh_token, access_expires_at) -> None:
        conn.execute(
            "UPDATE sessions SET access_token = ?, refresh_token = ?, access_expires_at = ?, "
            "last_revalidated_at = ?, refresh_lease_until = 0, revalidate_retry_at = 0 WHERE id_hash = ?",
            (access_token, refresh_token, access_expires_at, time.time(), id_hash),
        )

    @_threaded
    def fail_refresh(self, conn, id_hash) -> None:
        """Server unreachable: keep the session, retry in a few seconds."""
        conn.execute(
            "UPDATE sessions SET refresh_lease_until = 0, revalidate_retry_at = ? WHERE id_hash = ?",
            (time.time() + RETRY_BACKOFF, id_hash),
        )

    # --- logout tokens --------------------------------------------------

    @_threaded
    def mark_jti(self, conn, jti, expires_at) -> bool:
        """False if this logout token was already seen (replay)."""
        try:
            conn.execute("INSERT INTO seen_jti VALUES (?, ?)", (jti, expires_at))
        except sqlite3.IntegrityError:
            return False
        return True

    # --- housekeeping ---------------------------------------------------

    @_threaded
    def purge(self, conn) -> None:
        now = time.time()
        conn.execute("DELETE FROM login_attempts WHERE expires_at < ?", (now,))
        conn.execute("DELETE FROM seen_jti WHERE expires_at < ?", (now,))
        conn.execute(
            "DELETE FROM sessions WHERE absolute_expires_at < ? OR last_seen_at < ?",
            (now, now - self.idle_ttl),
        )
