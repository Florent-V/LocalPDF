export interface ToolNavItem {
  title: string
  description: string
  icon: string
  to: string
}

export interface ToolNavCategory {
  title: string
  icon: string
  color: 'indigo' | 'amber' | 'emerald' | 'sky' | 'fuchsia'
  tools: ToolNavItem[]
}

export const TOOL_CATEGORIES: ToolNavCategory[] = [
  {
    title: 'Organiser',
    icon: 'i-lucide-files',
    color: 'indigo',
    tools: [
      { title: 'Fusionner', description: 'Assemblez plusieurs PDF en un seul.', icon: 'i-lucide-merge', to: '/outils/fusionner' },
      { title: 'Diviser', description: 'Extrayez une ou plusieurs pages.', icon: 'i-lucide-scissors', to: '/outils/diviser' },
      { title: 'Organiser', description: 'Changez l\'ordre, supprimez ou pivotez des pages.', icon: 'i-lucide-arrow-up-down', to: '/outils/organiser' }
    ]
  },
  {
    title: 'Modifier',
    icon: 'i-lucide-pen-tool',
    color: 'amber',
    tools: [
      { title: 'Filigrane', description: 'Ajoutez un texte ou une image.', icon: 'i-lucide-stamp', to: '/outils/filigrane' },
      { title: 'Formulaire', description: 'Remplissez les champs d\'un formulaire PDF.', icon: 'i-lucide-clipboard-edit', to: '/outils/formulaire' }
    ]
  },
  {
    title: 'Sécurité',
    icon: 'i-lucide-shield',
    color: 'emerald',
    tools: [
      { title: 'Protéger', description: 'Chiffrez avec un mot de passe.', icon: 'i-lucide-lock', to: '/outils/proteger' },
      { title: 'Déverrouiller', description: 'Retirez le mot de passe.', icon: 'i-lucide-unlock', to: '/outils/deverrouiller' },
      { title: 'Censurer', description: 'Masquez des informations sensibles.', icon: 'i-lucide-eye-off', to: '/outils/censurer' }
    ]
  },
  {
    title: 'Convertir',
    icon: 'i-lucide-arrow-left-right',
    color: 'sky',
    tools: [
      { title: 'Images → PDF', description: 'Compilez des images.', icon: 'i-lucide-image', to: '/outils/images-vers-pdf' },
      { title: 'PDF → Images', description: 'Extrayez les pages en images.', icon: 'i-lucide-images', to: '/outils/pdf-vers-images' },
      { title: 'Office → PDF (in progress)', description: 'Convertissez Word, Excel, PowerPoint.', icon: 'i-lucide-file-spreadsheet', to: '/outils/office-vers-pdf' },
      { title: 'Markdown → PDF', description: 'Générez un PDF depuis du Markdown.', icon: 'i-lucide-file-text', to: '/outils/markdown-vers-pdf' },
      { title: 'PDF → Word (in progress)', description: 'Convertissez en document modifiable.', icon: 'i-lucide-file-type-2', to: '/outils/pdf-vers-word' }
    ]
  },
  {
    title: 'Intelligence (In progress)',
    icon: 'i-lucide-sparkles',
    color: 'fuchsia',
    tools: [
      { title: 'PDF → Markdown', description: 'Extrayez le texte structuré.', icon: 'i-lucide-file-code', to: '/outils/pdf-vers-markdown' },
      { title: 'Résumé', description: 'Résumé par IA.', icon: 'i-lucide-align-left', to: '/outils/resume' },
      { title: 'Traduction', description: 'Traduction par IA.', icon: 'i-lucide-languages', to: '/outils/traduction' },
      { title: 'Chat', description: 'Posez des questions à votre document.', icon: 'i-lucide-message-circle', to: '/outils/chat' }
    ]
  }
]
