/**
 * draw.io plugin for netbox-plugin-plan-drawing: links drawing elements (cells) to NetBox
 * objects.
 *
 * A link is stored as custom properties of the cell: netbox_type ('<app_label>.<model>'),
 * netbox_id, and netbox_display (the object's name at the time it was linked). The object
 * picker is provided by the NetBox page embedding draw.io (editor.js), reachable as
 * window.parent.netboxPlanDrawingEditor, since both are served from the same origin.
 *
 * Loaded by the bundled draw.io with ?p=netbox (registered in drawio-overrides/js/PostConfig.js).
 */
Draw.loadPlugin(function (ui) {
  'use strict';

  var TYPE = 'netbox_type';
  var ID = 'netbox_id';
  var DISPLAY = 'netbox_display';

  var graph = ui.editor.graph;
  var host = null;
  try {
    host = window.parent !== window ? window.parent.netboxPlanDrawingEditor || null : null;
  } catch (e) {
    host = null;
  }

  // A small badge marking linked cells in the editor (not saved with the drawing).
  var badge = new mxImage('data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">' +
    '<circle cx="8" cy="8" r="7.5" fill="#0d6efd"/>' +
    '<path d="M6.5 9.5l3-3M7 5.5l1-1a2 2 0 0 1 3 3l-1 1M9 10.5l-1 1a2 2 0 0 1-3-3l1-1" ' +
    'stroke="#fff" stroke-width="1.4" fill="none" stroke-linecap="round"/></svg>'), 16, 16);

  mxResources.parse(
    'netboxLink=Link to NetBox Object...\n' +
    'netboxUnlink=Remove NetBox Link\n');

  function getLink(cell) {
    var value = cell != null ? graph.getModel().getValue(cell) : null;
    if (mxUtils.isNode(value) && value.getAttribute(TYPE) && value.getAttribute(ID)) {
      return {
        type: value.getAttribute(TYPE),
        id: parseInt(value.getAttribute(ID), 10),
        display: value.getAttribute(DISPLAY) || (value.getAttribute(TYPE) + ':' + value.getAttribute(ID)),
      };
    }
    return null;
  }

  function setLink(cell, link) {
    var model = graph.getModel();
    var value = model.getValue(cell);
    var node;
    if (mxUtils.isNode(value)) {
      node = value.cloneNode(true);
    } else {
      node = mxUtils.createXmlDocument().createElement('object');
      node.setAttribute('label', value || '');
    }

    if (link) {
      node.setAttribute(TYPE, link.type);
      node.setAttribute(ID, String(link.id));
      node.setAttribute(DISPLAY, link.display);
      if (!node.getAttribute('label')) {
        node.setAttribute('label', link.display);
      }
    } else {
      node.removeAttribute(TYPE);
      node.removeAttribute(ID);
      node.removeAttribute(DISPLAY);
    }

    model.beginUpdate();
    try {
      model.setValue(cell, node);
    } finally {
      model.endUpdate();
    }
  }

  function selectedCell() {
    return graph.getSelectionCount() === 1 ? graph.getSelectionCell() : null;
  }

  function linkSelection() {
    var cell = selectedCell();
    if (cell == null || host == null) {
      return;
    }
    host.pick(getLink(cell), function (link) {
      setLink(cell, link);
      notifySelection();
    });
  }

  function unlinkSelection() {
    var cell = selectedCell();
    if (cell != null && getLink(cell)) {
      setLink(cell, null);
      notifySelection();
    }
  }

  ui.actions.addAction('netboxLink', linkSelection).isEnabled = function () {
    return host != null && selectedCell() != null;
  };
  ui.actions.addAction('netboxUnlink', unlinkSelection).isEnabled = function () {
    return getLink(selectedCell()) != null;
  };

  // Context menu entries
  var createPopupMenu = ui.menus.createPopupMenu;
  ui.menus.createPopupMenu = function (menu, cell, evt) {
    createPopupMenu.apply(this, arguments);
    var selected = selectedCell();
    if (selected != null) {
      menu.addSeparator();
      this.addMenuItems(menu, getLink(selected) ? ['netboxLink', 'netboxUnlink'] : ['netboxLink'], null, evt);
    }
  };

  // Badges on linked cells; clicking one opens the picker.
  function refreshBadges() {
    var model = graph.getModel();
    var cells = model.getDescendants(model.getRoot());
    for (var i = 0; i < cells.length; i++) {
      var cell = cells[i];
      if (!model.isVertex(cell) && !model.isEdge(cell)) {
        continue;
      }
      var overlays = graph.getCellOverlays(cell) || [];
      for (var j = overlays.length - 1; j >= 0; j--) {
        if (overlays[j].netbox) {
          graph.removeCellOverlay(cell, overlays[j]);
        }
      }
      var link = getLink(cell);
      if (link) {
        var overlay = new mxCellOverlay(badge, link.display + ' (' + link.type + ')',
          mxConstants.ALIGN_RIGHT, mxConstants.ALIGN_TOP);
        overlay.netbox = true;
        overlay.cursor = 'pointer';
        overlay.addListener(mxEvent.CLICK, mxUtils.bind(null, function (target) {
          graph.setSelectionCell(target);
          linkSelection();
        }, cell));
        graph.addCellOverlay(cell, overlay);
      }
    }
  }

  var badgeTimer = null;
  function scheduleBadges() {
    clearTimeout(badgeTimer);
    badgeTimer = setTimeout(refreshBadges, 50);
  }

  function notifySelection() {
    if (host == null) {
      return;
    }
    var cell = selectedCell();
    if (cell == null) {
      host.selectionChanged(null);
      return;
    }
    // Labels may contain HTML; DOMParser does not run scripts or load images.
    var label = graph.convertValueToString(cell) || '';
    label = new DOMParser().parseFromString(label, 'text/html').body.textContent || '';
    host.selectionChanged({ label: label.replace(/\s+/g, ' ').trim(), link: getLink(cell) });
  }

  graph.getSelectionModel().addListener(mxEvent.CHANGE, notifySelection);
  graph.getModel().addListener(mxEvent.CHANGE, function () {
    scheduleBadges();
    notifySelection();
  });
  ui.editor.addListener('resetGraphView', scheduleBadges);
  ui.addListener('currentPageChanged', scheduleBadges);
  ui.editor.addListener('statusChanged', function () {
    if (host != null && host.modifiedChanged) {
      host.modifiedChanged(ui.editor.modified);
    }
  });

  if (host != null) {
    host.register({
      linkSelection: linkSelection,
      unlinkSelection: unlinkSelection,
    });
  }
  scheduleBadges();
});
