export function registerServiceWorker() {
  if (import.meta.env.DEV) {
    console.log('Service Worker não registrado em ambiente de desenvolvimento.');
    return;
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registrado com sucesso:', registration.scope);

          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('Nova versão da PWA disponível. Recarregando...');
                  // Em uma implementação mais complexa, exibiríamos um toast aqui.
                  // Para garantir a versão fresca agora, damos um reload.
                  window.location.reload();
                }
              });
            }
          });
        })
        .catch((error) => {
          console.error('Falha ao registrar o Service Worker:', error);
        });
    });
  }
}
