export interface ToolNavItem {
  title: string
  description: string
  icon: string
  to: string
}

export type ToolNavColor = 'indigo' | 'amber' | 'emerald' | 'sky' | 'fuchsia'

export interface ToolNavCategory {
  title: string
  icon: string
  color: ToolNavColor
  tools: ToolNavItem[]
}

// Single source of truth for the per-category accent color, shared by
// ToolCard, AppSidebar and AppMobileNav (previously three copies of the
// same color-to-Tailwind-class map).
export const TOOL_COLOR_BADGE: Record<ToolNavColor, string> = {
  indigo: 'text-indigo-500 bg-indigo-500/10',
  amber: 'text-amber-500 bg-amber-500/10',
  emerald: 'text-emerald-500 bg-emerald-500/10',
  sky: 'text-sky-500 bg-sky-500/10',
  fuchsia: 'text-fuchsia-500 bg-fuchsia-500/10'
}

export const TOOL_COLOR_BADGE_HOVER: Record<ToolNavColor, string> = {
  indigo: 'group-hover:bg-indigo-500/15',
  amber: 'group-hover:bg-amber-500/15',
  emerald: 'group-hover:bg-emerald-500/15',
  sky: 'group-hover:bg-sky-500/15',
  fuchsia: 'group-hover:bg-fuchsia-500/15'
}

export const TOOL_COLOR_HOVER_BORDER: Record<ToolNavColor, string> = {
  indigo: 'hover:border-indigo-500/60',
  amber: 'hover:border-amber-500/60',
  emerald: 'hover:border-emerald-500/60',
  sky: 'hover:border-sky-500/60',
  fuchsia: 'hover:border-fuchsia-500/60'
}

export const TOOL_COLOR_ACTIVE_BORDER: Record<ToolNavColor, string> = {
  indigo: 'border-indigo-500',
  amber: 'border-amber-500',
  emerald: 'border-emerald-500',
  sky: 'border-sky-500',
  fuchsia: 'border-fuchsia-500'
}

export const TOOL_CATEGORIES: ToolNavCategory[] = [
  {
    title: 'Organiser',
    icon: 'i-lucide-files',
    color: 'indigo',
    tools: [
      { title: 'Fusionner', description: 'Assemblez plusieurs PDF en un seul.', icon: 'i-lucide-merge', to: '/tools/merge' },
      { title: 'Diviser', description: 'Extrayez une ou plusieurs pages.', icon: 'i-lucide-scissors', to: '/tools/split' },
      { title: 'Organiser', description: 'Changez l\'ordre, supprimez ou pivotez des pages.', icon: 'i-lucide-arrow-up-down', to: '/tools/organize' }
    ]
  },
  {
    title: 'Modifier',
    icon: 'i-lucide-pen-tool',
    color: 'amber',
    tools: [
      { title: 'Filigrane', description: 'Ajoutez un texte ou une image.', icon: 'i-lucide-stamp', to: '/tools/watermark' },
      { title: 'Formulaire', description: 'Remplissez les champs d\'un formulaire PDF.', icon: 'i-lucide-clipboard-edit', to: '/tools/form' }
    ]
  },
  {
    title: 'Sécurité',
    icon: 'i-lucide-shield',
    color: 'emerald',
    tools: [
      { title: 'Protéger', description: 'Chiffrez avec un mot de passe.', icon: 'i-lucide-lock', to: '/tools/protect' },
      { title: 'Déverrouiller', description: 'Retirez le mot de passe.', icon: 'i-lucide-unlock', to: '/tools/unlock' },
      { title: 'Censurer', description: 'Masquez des informations sensibles.', icon: 'i-lucide-eye-off', to: '/tools/redact' }
    ]
  },
  {
    title: 'Convertir',
    icon: 'i-lucide-arrow-left-right',
    color: 'sky',
    tools: [
      { title: 'Images → PDF', description: 'Compilez des images.', icon: 'i-lucide-image', to: '/tools/images-to-pdf' },
      { title: 'PDF → Images', description: 'Extrayez les pages en images.', icon: 'i-lucide-images', to: '/tools/pdf-to-images' },
      { title: 'Office → PDF (in progress)', description: 'Convertissez Word, Excel, PowerPoint.', icon: 'i-lucide-file-spreadsheet', to: '/tools/office-to-pdf' },
      { title: 'Markdown → PDF', description: 'Générez un PDF depuis du Markdown.', icon: 'i-lucide-file-text', to: '/tools/markdown-to-pdf' },
      { title: 'PDF → Word (in progress)', description: 'Convertissez en document modifiable.', icon: 'i-lucide-file-type-2', to: '/tools/pdf-to-word' }
    ]
  },
  {
    title: 'Intelligence (In progress)',
    icon: 'i-lucide-sparkles',
    color: 'fuchsia',
    tools: [
      { title: 'PDF → Markdown', description: 'Extrayez le texte structuré.', icon: 'i-lucide-file-code', to: '/tools/pdf-to-markdown' },
      { title: 'Résumé', description: 'Résumé par IA.', icon: 'i-lucide-align-left', to: '/tools/summarize' },
      { title: 'Traduction', description: 'Traduction par IA.', icon: 'i-lucide-languages', to: '/tools/translate' },
      { title: 'Chat', description: 'Posez des questions à votre document.', icon: 'i-lucide-message-circle', to: '/tools/chat' }
    ]
  }
]
