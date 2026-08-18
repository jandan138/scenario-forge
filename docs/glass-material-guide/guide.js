document.querySelectorAll('[data-comparison]').forEach((card) => {
  const range = card.querySelector('.split-control');
  const stage = card.querySelector('.split-stage');
  const layer = card.querySelector('.after-layer');
  const afterImage = layer.querySelector('img');
  const divider = card.querySelector('.divider');
  const sync = () => {
    const value = `${range.value}%`;
    afterImage.style.width = `${stage.clientWidth}px`;
    layer.style.width = value;
    divider.style.left = value;
  };
  range.addEventListener('input', sync);
  window.addEventListener('resize', sync);
  sync();
});
