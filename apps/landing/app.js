// Local UI only: no backend, credentials, storage, analytics, or live feeds.
const routeButtons = [...document.querySelectorAll('[data-route]')];
const status = document.querySelector('#demo-status');
const routePath = document.querySelector('#map-route');
const alternatePath = document.querySelector('#map-secondary');
const paths = {
  metro: 'M150 350L175 285L282 250L328 138L424 99',
  bus: 'M150 350L193 243L293 212L350 118L424 99',
};
routeButtons.forEach((button) => {
  button.addEventListener('click', () => {
    routeButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    const bus = button.dataset.route === 'bus';
    routePath.setAttribute('d', paths[bus ? 'bus' : 'metro']);
    alternatePath.setAttribute('d', paths[bus ? 'metro' : 'bus']);
    status.textContent = `${bus ? 'Bus' : 'Metro'} selected. Synthetic times; not travel advice.`;
  });
});
let reversed = false;
document.querySelector('.swap').addEventListener('click', () => {
  reversed = !reversed;
  const labels = document.querySelectorAll('.stops > span:not(.stop-line)');
  labels[0].lastChild.textContent = reversed ? 'Namma Park' : 'Namma West';
  labels[1].lastChild.textContent = reversed ? 'Namma West' : 'Namma Park';
  const mapLabels = document.querySelectorAll('.map svg g[filter] text');
  mapLabels[0].textContent = `${reversed ? 'B' : 'A'} · Namma West (synthetic)`;
  mapLabels[1].textContent = `${reversed ? 'A' : 'B'} · Namma Park (synthetic)`;
  status.textContent = 'Direction swapped. Synthetic times; not travel advice.';
});
const menuButton = document.querySelector('.menu');
const mobileMenu = document.querySelector('#mobile-menu');
function closeMenu() {
  mobileMenu.hidden = true;
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-label', 'Open navigation');
}
menuButton.addEventListener('click', () => {
  const opening = mobileMenu.hidden;
  mobileMenu.hidden = !opening;
  menuButton.setAttribute('aria-expanded', String(opening));
  menuButton.setAttribute('aria-label', opening ? 'Close navigation' : 'Open navigation');
});
mobileMenu.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !mobileMenu.hidden) { closeMenu(); menuButton.focus(); }
});
window.matchMedia('(min-width: 481px)').addEventListener('change', closeMenu);
