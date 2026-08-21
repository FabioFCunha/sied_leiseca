/**
 * Executa o compartilhamento do resumo do relatório.
 *
 * Tenta usar a Web Share API (navigator.share) quando disponível.
 * Se indisponível ou se ocorrer erro técnico, redireciona para wa.me.
 *
 * Retorna um objeto { status, url? } indicando o resultado:
 *  - "shared"     : navigator.share concluiu com sucesso.
 *  - "cancelled"  : usuário cancelou (AbortError).
 *  - "redirected" : redirecionamento para wa.me foi iniciado.
 *  - "empty"      : não havia resumo para compartilhar.
 *
 * @param {string} text - Texto do resumo a ser compartilhado.
 * @param {object} deps - Dependências injetáveis para teste.
 * @param {function} [deps.navigatorShare] - navigator.share.bind(navigator) ou undefined.
 * @param {function} deps.locationAssign - (url) => window.location.assign(url).
 * @returns {Promise<{status: string, url?: string}>}
 */
export async function executeShare(text, { navigatorShare, locationAssign }) {
  if (!text) return { status: "empty" };

  if (typeof navigatorShare === "function") {
    try {
      await navigatorShare({
        title: "Relatório Técnico - Operação Lei Seca",
        text,
      });
      return { status: "shared" };
    } catch (error) {
      if (error?.name === "AbortError") {
        return { status: "cancelled" };
      }
      // Falha técnica — cairá no fallback abaixo
    }
  }

  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(text)}`;
  locationAssign(whatsappUrl);

  return { status: "redirected", url: whatsappUrl };
}
