Le "Prompt de Transition" (À utiliser entre chaque phase)
Quand tu as terminé la Phase 1 avec l'IA (et que le projet tourne sur ta machine), ne donne pas la Phase 2 dans la même discussion. La mémoire de l'IA sera saturée de vieux code.

Utilise ce prompt dans la discussion en cours :

"La Phase [X] est terminée et fonctionne parfaitement. Génère-moi maintenant un fichier STATE.md. Ce fichier doit contenir un résumé technique extrêmement précis de ce qui a été construit jusqu'à présent : la structure exacte des dossiers, les ports utilisés, les conventions de nommage choisies, l'état du backend, l'état du frontend, et les librairies installées. Ce fichier me servira de contexte pour initier une nouvelle session d'IA pour la phase suivante."

Ensuite :

Tu copies la réponse (STATE.md).

Tu ouvres une nouvelle conversation avec l'IA.

Tu lui donnes : Le 00_MASTER_PROMPT.md + Le STATE.md + Le fichier 02_PHASE_2_MODIF_SECURITY.md.
