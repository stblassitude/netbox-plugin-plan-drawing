/**
 * Plan drawing editor: embeds the bundled draw.io, loads the drawing into it, and saves it
 * back to NetBox. Talks to draw.io through its embed protocol (JSON messages), and to the
 * NetBox draw.io plugin (drawio-netbox.js) through window.netboxPlanDrawingEditor; draw.io is
 * served from the same origin, so the plugin can call it directly.
 */
(function () {
  'use strict';

  const config = JSON.parse(document.getElementById('plan-drawing-editor-config').textContent);
  const frame = document.getElementById('plan-drawing-frame');
  const statusText = document.getElementById('plan-drawing-status');
  const selectionText = document.getElementById('plan-drawing-selection');
  const linkButton = document.getElementById('plan-drawing-link');
  const unlinkButton = document.getElementById('plan-drawing-unlink');
  const TYPE_STORAGE_KEY = 'netbox-plan-drawing-object-type';

  let lastUpdated = config.last_updated;
  let modified = false;
  let plugin = null;

  function setStatus(message, level) {
    statusText.textContent = message || '';
    statusText.className = 'align-self-center me-2 ' + (level ? 'text-' + level : 'text-muted');
  }

  function post(message) {
    frame.contentWindow.postMessage(JSON.stringify(message), window.location.origin);
  }

  //
  // Saving
  //

  async function save(xml, exit) {
    setStatus('Saving…');
    post({ action: 'spinner', show: true, messageKey: 'saving' });
    let response, result;
    try {
      response = await fetch(config.save_url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': config.csrf_token,
        },
        body: JSON.stringify({ content: xml, last_updated: lastUpdated }),
      });
      result = await response.json().catch(function () {
        return {};
      });
    } catch (e) {
      response = null;
      result = { error: 'Could not reach NetBox: ' + e.message };
    }
    post({ action: 'spinner', show: false });

    if (response && response.ok) {
      lastUpdated = result.last_updated;
      modified = false;
      post({ action: 'status', message: '', modified: false });
      const count = result.element_count;
      setStatus('Saved; ' + count + ' linked element' + (count === 1 ? '' : 's') + '.', 'success');
      if (exit) {
        window.location.href = config.exit_url;
      }
      return;
    }

    let message = (result && result.error) || ('Saving failed (' + (response ? response.status : 'network error') + ')');
    if (response && response.status === 409) {
      message += ' Your changes have not been saved. Copy them (e.g. File > Export as > XML) and reload the page.';
    }
    setStatus(message, 'danger');
    post({ action: 'dialog', title: 'Saving failed', message: message, button: 'OK', modified: true });
  }

  //
  // draw.io embed protocol
  //

  window.addEventListener('message', function (evt) {
    if (evt.source !== frame.contentWindow || evt.origin !== window.location.origin || typeof evt.data !== 'string') {
      return;
    }
    let message;
    try {
      message = JSON.parse(evt.data);
    } catch (e) {
      return;
    }

    switch (message.event) {
      case 'configure':
        post({
          action: 'configure',
          config: {
            compressXml: false,
            // Online font and image sources are not available.
            defaultFonts: ['Helvetica', 'Verdana', 'Times New Roman', 'Garamond', 'Courier New'],
            customFonts: [],
          },
        });
        break;
      case 'init':
        post({
          action: 'load',
          xml: config.content || '',
          title: config.title,
          autosave: 0,
          saveAndExit: '1',
          noExitBtn: '0',
        });
        setStatus('');
        break;
      case 'save':
        save(message.xml, message.exit);
        break;
      case 'exit':
        window.location.href = config.exit_url;
        break;
    }
  });

  window.addEventListener('beforeunload', function (evt) {
    if (modified) {
      evt.preventDefault();
    }
  });

  //
  // Object picker
  //

  const picker = {
    root: document.getElementById('plan-drawing-picker'),
    type: document.getElementById('plan-drawing-picker-type'),
    search: document.getElementById('plan-drawing-picker-search'),
    results: document.getElementById('plan-drawing-picker-results'),
    current: document.getElementById('plan-drawing-picker-current'),
    cancel: document.getElementById('plan-drawing-picker-cancel'),
    callback: null,
    timer: null,
    request: 0,
  };

  config.object_types.forEach(function (objectType) {
    const option = document.createElement('option');
    option.value = objectType.value;
    option.textContent = objectType.label;
    picker.type.appendChild(option);
  });

  function objectType(value) {
    return config.object_types.find(function (t) {
      return t.value === value;
    });
  }

  function secondaryText(result) {
    const parent = result.device || result.module || result.rack || result.location || result.site ||
      result.power_panel || result.circuit || result.provider;
    return parent && parent.display ? parent.display : (result.description || '');
  }

  function renderMessage(text) {
    picker.results.replaceChildren();
    const item = document.createElement('div');
    item.className = 'list-group-item text-muted';
    item.textContent = text;
    picker.results.appendChild(item);
  }

  async function runSearch() {
    const type = objectType(picker.type.value);
    if (!type) {
      return;
    }
    const request = ++picker.request;
    const params = new URLSearchParams({ brief: '1', limit: '50' });
    if (picker.search.value.trim()) {
      params.set('q', picker.search.value.trim());
    }
    renderMessage('Searching…');
    let data;
    try {
      const response = await fetch(type.api_url + '?' + params.toString(), {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      data = await response.json();
    } catch (e) {
      if (request === picker.request) {
        renderMessage('Search failed: ' + e.message);
      }
      return;
    }
    if (request !== picker.request) {
      return;
    }

    picker.results.replaceChildren();
    if (!data.results || data.results.length === 0) {
      renderMessage('No matching objects.');
      return;
    }
    data.results.forEach(function (result) {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      const title = document.createElement('div');
      title.className = 'fw-semibold';
      title.textContent = result.display;
      item.appendChild(title);
      const secondary = secondaryText(result);
      if (secondary) {
        const small = document.createElement('small');
        small.className = 'text-muted';
        small.textContent = secondary;
        item.appendChild(small);
      }
      item.addEventListener('click', function () {
        closePicker({ type: type.value, id: result.id, display: result.display });
      });
      picker.results.appendChild(item);
    });
    if (data.count > data.results.length) {
      renderMore(data.count - data.results.length);
    }
  }

  function renderMore(count) {
    const item = document.createElement('div');
    item.className = 'list-group-item small text-muted';
    item.textContent = count + ' more; refine the search to narrow the results.';
    picker.results.appendChild(item);
  }

  function openPicker(current, callback) {
    picker.callback = callback;
    let type = current && objectType(current.type) ? current.type : null;
    if (!type) {
      try {
        type = localStorage.getItem(TYPE_STORAGE_KEY);
      } catch (e) {
        type = null;
      }
    }
    if (type && objectType(type)) {
      picker.type.value = type;
    }
    picker.current.textContent = current ? 'Currently linked to: ' + current.display + ' (' + current.type + ')' : '';
    picker.search.value = '';
    picker.root.hidden = false;
    picker.search.focus();
    runSearch();
  }

  function closePicker(result) {
    picker.root.hidden = true;
    const callback = picker.callback;
    picker.callback = null;
    if (result) {
      try {
        localStorage.setItem(TYPE_STORAGE_KEY, result.type);
      } catch (e) {
        // ignore
      }
    }
    if (callback && result) {
      callback(result);
    }
    frame.focus();
  }

  picker.type.addEventListener('change', runSearch);
  picker.search.addEventListener('input', function () {
    clearTimeout(picker.timer);
    picker.timer = setTimeout(runSearch, 250);
  });
  picker.cancel.addEventListener('click', function () {
    closePicker(null);
  });
  picker.root.addEventListener('click', function (evt) {
    if (evt.target === picker.root) {
      closePicker(null);
    }
  });
  document.addEventListener('keydown', function (evt) {
    if (evt.key === 'Escape' && !picker.root.hidden) {
      closePicker(null);
    }
  });

  //
  // Interface for the draw.io plugin
  //

  function showSelection(selection) {
    linkButton.disabled = !selection;
    unlinkButton.disabled = !(selection && selection.link);
    if (!selection) {
      selectionText.textContent = 'none';
      selectionText.className = 'text-muted';
      return;
    }
    selectionText.className = '';
    const label = selection.label || 'unlabeled element';
    selectionText.textContent = selection.link
      ? label + ' → ' + selection.link.display + ' (' + selection.link.type + ')'
      : label + ' (not linked)';
  }

  window.netboxPlanDrawingEditor = {
    /** Called by the plugin once draw.io has loaded it. */
    register: function (api) {
      plugin = api;
    },
    /** Asks the user to pick a NetBox object; calls callback({type, id, display}). */
    pick: openPicker,
    /** The selection changed: null, or {label, link: null | {type, id, display}}. */
    selectionChanged: showSelection,
    /** The drawing was modified or saved in draw.io. */
    modifiedChanged: function (value) {
      modified = value;
    },
  };

  linkButton.addEventListener('click', function () {
    if (plugin) {
      plugin.linkSelection();
    }
  });
  unlinkButton.addEventListener('click', function () {
    if (plugin) {
      plugin.unlinkSelection();
    }
  });

  setStatus('Loading draw.io…');
  frame.src = frame.dataset.src;
})();
