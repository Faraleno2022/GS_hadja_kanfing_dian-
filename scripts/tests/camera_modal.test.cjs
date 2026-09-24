/* Simule le navigateur sans accès à une caméra ni aux données de l'école. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../../templates/eleves/partials/_camera_modal.html'), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const flush = () => new Promise(resolve => setImmediate(resolve));

function surface() {
  function element() {
    const listeners = {};
    return {
      listeners, disabled: true, style: {}, classList: {add() {}, remove() {}},
      addEventListener(name, fn) { listeners[name] = fn; },
      dispatchEvent(event) { if (listeners[event.type]) listeners[event.type](event); },
      fire(name, data = {}) { return listeners[name]?.({preventDefault() {}, ...data}); },
    };
  }
  const names = ['cameraModal', 'cameraVideo', 'cameraCanvas', 'btnCapture', 'btnUse', 'btnSwitch', 'cameraError', 'id_photo'];
  const elements = Object.fromEntries(names.map(name => [name, element()]));
  const video = elements.cameraVideo;
  Object.assign(video, {videoWidth: 1280, videoHeight: 720, readyState: 2});
  let captured = 0;
  elements.cameraCanvas.getContext = () => ({clearRect() {}, drawImage() { captured++; }});
  elements.cameraCanvas.toBlob = callback => callback({size: 500});
  const requests = [];
  const document = element();
  document.getElementById = name => elements[name];
  document.querySelector = () => null;
  const window = element();
  window.isSecureContext = true;
  const modal = {show() { elements.cameraModal.fire('shown.bs.modal'); }, hide() { elements.cameraModal.fire('hidden.bs.modal'); }};
  const bootstrap = {Modal: {getOrCreateInstance: () => modal, getInstance: () => modal}};
  const navigator = {
    permissions: {query: async () => ({state: 'prompt'})},
    mediaDevices: {getUserMedia: () => new Promise((resolve, reject) => requests.push({resolve, reject}))},
  };
  class DataTransfer {
    constructor() { this.files = []; this.items = {add: item => this.files.push(item)}; }
  }
  vm.runInNewContext(source, {document, window, navigator, bootstrap, location: {hostname: 'localhost'},
    console: {warn() {}, error() {}}, URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    DataTransfer, File: class {constructor(parts, name) { this.name = name; }}, Event: class {constructor(type) { this.type = type; }} });
  const open = () => document.fire('click', {target: {closest: () => ({getAttribute: () => 'id_photo'})}});
  function stream() {
    const track = {stopped: false, stop() { this.stopped = true; }};
    return {track, getTracks: () => [track]};
  }
  return {elements, requests, open, stream, captured: () => captured};
}

(async () => {
  const s = surface();
  s.elements.btnCapture.fire('click');
  s.elements.btnUse.fire('click');
  assert.equal(s.captured(), 0);
  assert.equal(s.elements.id_photo.files, undefined);
  s.open(); await flush();
  const live = s.stream(); s.requests[0].resolve(live); await flush();
  s.elements.cameraVideo.fire('loadeddata');
  assert.equal(s.elements.btnCapture.disabled, false);
  s.elements.btnCapture.fire('click');
  assert.equal(s.captured(), 1);
  assert.equal(s.elements.btnUse.disabled, false);
  s.elements.btnUse.fire('click');
  assert.equal(s.elements.id_photo.files[0].name, 'photo.jpg');
  assert.equal(live.track.stopped, true);

  const late = surface(); late.open(); await flush();
  late.elements.cameraModal.fire('hidden.bs.modal');
  const lateStream = late.stream(); late.requests[0].resolve(lateStream); await flush();
  assert.equal(lateStream.track.stopped, true);
  assert.equal(late.elements.cameraVideo.srcObject, null);

  const switcher = surface(); switcher.open(); await flush();
  switcher.elements.btnSwitch.fire('click'); await flush();
  const old = switcher.stream(), current = switcher.stream();
  switcher.requests[1].resolve(current); await flush();
  switcher.requests[0].resolve(old); await flush();
  assert.equal(old.track.stopped, true);
  assert.equal(current.track.stopped, false);
  assert.equal(switcher.elements.cameraVideo.srcObject, current);

  const denied = surface(); denied.open(); await flush();
  denied.requests[0].reject(new Error('denied')); await flush();
  denied.requests[1].reject({name: 'NotAllowedError'}); await flush();
  assert.match(denied.elements.cameraError.innerHTML, /Permission/);
  assert.equal(denied.elements.btnCapture.disabled, true);
  assert.equal(denied.elements.btnUse.disabled, true);
  process.stdout.write('4 scénarios caméra réussis : capture, fermeture, bascule et refus.\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
