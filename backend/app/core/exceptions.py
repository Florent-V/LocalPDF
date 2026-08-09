class PDFToolException(Exception):
    """Exception métier de LocalPDF."""


class PasswordError(PDFToolException):
    """Erreur liée à un mot de passe PDF incorrect ou manquant."""
