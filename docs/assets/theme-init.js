/* Aplica a escolha de tema salva (se houver) antes do primeiro paint,
   pra não piscar o tema errado. Deliberadamente síncrono e minúsculo —
   deve ser carregado no <head>, antes do <link> do site.css. */
(function(){
  try{
    var t = localStorage.getItem('ic-theme');
    if (t === 'dark' || t === 'light') {
      document.documentElement.setAttribute('data-theme', t);
    }
  }catch(e){}
})();
