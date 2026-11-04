export function Icon({ name }: { name: 'mic' | 'plus' | 'send' | 'stop' | 'search' | 'compose' }) {
  return <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {name === 'compose' ? <><path d="M12 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-7" /><path d="m16 3 5 5M10 14l-1 4 4-1L22 8a2.1 2.1 0 0 0-5-5Z" /></> : name === 'mic' ? <><rect x="9" y="2" width="6" height="13" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" /></> : name === 'plus' ? <path d="M12 5v14M5 12h14" /> : name === 'send' ? <path d="M12 19V5M6 11l6-6 6 6" /> : name === 'search' ? <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></> : <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none" />}
  </svg>;
}
