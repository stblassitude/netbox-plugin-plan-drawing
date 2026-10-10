/**
 * Plan drawing viewer: shows the drawing with draw.io's viewer, and connects the drawing with
 * the list of elements linked to NetBox objects: clicking either one highlights the other,
 * searching the list highlights all matching elements, and ?highlight=<type>:<id> in the page
 * URL highlights the elements of that object when the page opens. The list shows the elements
 * of the current page, or of all pages. A selected location or rack lists the objects in it;
 * clicking those that are linked in the drawing as well selects their elements.
 */
(function () {
  'use strict';

  const script = document.currentScript;
  const base = script.dataset.drawioBase;

  // Point draw.io's viewer at the bundled copy instead of viewer.diagrams.net.
  Object.assign(window, {
    DRAWIO_BASE_URL: base,
    DRAWIO_SERVER_URL: base,
    DRAWIO_LIGHTBOX_URL: base,
    STYLE_PATH: base + 'styles',
    SHAPES_PATH: base + 'shapes',
    STENCIL_PATH: base + 'stencils',
    GRAPH_IMAGE_PATH: base + 'img',
    RESOURCES_PATH: base + 'resources',
    mxBasePath: base + 'mxgraph/',
    mxImageBasePath: base + 'mxgraph/images',
    mxLoadResources: false,
    mxLoadStylesheets: false,
  });

  // Defined in plan-drawing.css, so that the element list uses the same color.
  const SELECT_COLOR = getComputedStyle(document.documentElement)
    .getPropertyValue('--plan-drawing-select-color').trim() || '#0d6efd';
  const MATCH_COLOR = '#fd7e14';
  const HOVER_COLOR = '#20c997';
  const BORDER = 16;

  function readJson(id) {
    return JSON.parse(document.getElementById(id).textContent);
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function PlanDrawingViewer(container, content, elements) {
    this.container = container;
    this.elements = elements;
    this.rows = Array.from(document.querySelectorAll('.plan-drawing-element'));
    this.nodes = Array.from(document.querySelectorAll('.plan-drawing-node-linked'));
    this.highlights = [];
    this.hoverHighlights = [];
    this.selected = [];
    this.matches = [];
    this.searchTerms = [];
    this.pageFilter = 'page';

    // The viewer sizes itself to the drawing unless the container has an explicit size; the
    // container scrolls instead, and the drawing is fitted into it.
    container.style.width = '100%';
    container.style.height = container.offsetHeight + 'px';
    const xml = mxUtils.parseXml(content).documentElement;
    this.viewer = new GraphViewer(container, xml, {
      highlight: SELECT_COLOR,
      nav: true,
      lightbox: false,
      resize: false,
      border: BORDER,
    });
    this.graph = this.viewer.graph;
    container.style.height = '';
    container.style.overflow = 'auto';
    this.graph.setPanning(true);
    this.graph.panningHandler.useLeftButtonForPanning = true;
    this.graph.panningHandler.ignoreCell = true;

    this.installPageHook();
    this.installToolbar();
    this.installGraphHooks();
    this.installListHooks();
    this.updateList();
    this.fit();
  }

  PlanDrawingViewer.prototype.fit = function () {
    const graph = this.graph;
    graph.maxFitScale = 2;
    graph.fit(BORDER);
    graph.maxFitScale = null;

    // Center the drawing in the free space. (graph.center() only scrolls a container that has
    // scrollbars, and does not move the drawing when it fits.)
    const bounds = graph.getGraphBounds();
    const scale = graph.view.scale;
    const translate = graph.view.translate;
    const dx = Math.max(0, (this.container.clientWidth - bounds.width) / 2 - bounds.x);
    const dy = Math.max(0, (this.container.clientHeight - bounds.height) / 2 - bounds.y);
    graph.view.setTranslate(translate.x + dx / scale, translate.y + dy / scale);
  };

  PlanDrawingViewer.prototype.installToolbar = function () {
    const self = this;
    const pageSelect = document.getElementById('plan-drawing-page');
    const diagrams = Array.from(this.viewer.diagrams || []);
    this.multiPage = diagrams.length > 1;
    if (pageSelect && this.multiPage) {
      diagrams.forEach(function (diagram, index) {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = diagram.getAttribute('name') || ('Page ' + (index + 1));
        pageSelect.appendChild(option);
      });
      pageSelect.value = this.viewer.currentPage;
      document.getElementById('plan-drawing-page-group').hidden = false;
      pageSelect.addEventListener('change', function () {
        self.viewer.selectPage(parseInt(pageSelect.value, 10));
      });
    }
    this.pageSelect = pageSelect;

    const buttons = {
      'plan-drawing-zoom-in': function () { self.graph.zoomIn(); },
      'plan-drawing-zoom-out': function () { self.graph.zoomOut(); },
      'plan-drawing-zoom-fit': function () { self.fit(); },
    };
    Object.keys(buttons).forEach(function (id) {
      const button = document.getElementById(id);
      if (button) {
        button.addEventListener('click', buttons[id]);
      }
    });
  };

  PlanDrawingViewer.prototype.currentPageId = function () {
    const diagrams = this.viewer.diagrams;
    if (!diagrams || diagrams.length === 0) {
      return '';
    }
    return diagrams[this.viewer.currentPage].getAttribute('id') || String(this.viewer.currentPage);
  };

  PlanDrawingViewer.prototype.selectPageById = function (pageId) {
    if (pageId && pageId !== this.currentPageId()) {
      this.viewer.selectPageById(pageId);
    }
  };

  PlanDrawingViewer.prototype.installPageHook = function () {
    const self = this;
    const selectPage = this.viewer.selectPage;
    if (!selectPage) {
      return;
    }
    this.viewer.selectPage = function () {
      const result = selectPage.apply(this, arguments);
      if (self.pageSelect) {
        self.pageSelect.value = self.viewer.currentPage;
      }
      self.fit();
      self.updateList();
      self.refreshHighlights();
      return result;
    };
  };

  /** Returns the element indices on the current page linked to the given cell. */
  PlanDrawingViewer.prototype.elementsForCell = function (cell) {
    const pageId = this.currentPageId();
    const result = [];
    for (let cur = cell; cur != null; cur = this.graph.getModel().getParent(cur)) {
      this.elements.forEach(function (element, index) {
        if (element.cell_id === cur.id && element.page_id === pageId) {
          result.push(index);
        }
      });
      if (result.length > 0) {
        break;
      }
    }
    return result;
  };

  PlanDrawingViewer.prototype.cellForElement = function (index) {
    const element = this.elements[index];
    if (element.page_id !== this.currentPageId()) {
      return null;
    }
    return this.graph.getModel().getCell(element.cell_id);
  };

  PlanDrawingViewer.prototype.installGraphHooks = function () {
    const self = this;
    const graph = this.graph;

    // The viewer's graph is not enabled, so it fires no click events; a click is a mouse down
    // and up on the same spot (as opposed to panning).
    let down = null;
    graph.addMouseListener({
      mouseDown: function (sender, me) {
        down = { x: me.getX(), y: me.getY(), cell: me.getCell() };
      },
      mouseMove: function () {},
      mouseUp: function (sender, me) {
        if (down && Math.abs(me.getX() - down.x) < 4 && Math.abs(me.getY() - down.y) < 4) {
          const cell = me.getCell() || down.cell;
          self.select(cell ? self.elementsForCell(cell) : [], { scrollList: true });
        }
        down = null;
      },
    });

    const getCursorForCell = graph.getCursorForCell;
    graph.getCursorForCell = function (cell) {
      if (self.elementsForCell(cell).length > 0) {
        return 'pointer';
      }
      return getCursorForCell.apply(this, arguments);
    };

    const getTooltipForCell = graph.getTooltipForCell;
    graph.setTooltips(true);
    graph.getTooltipForCell = function (cell) {
      const indices = self.elementsForCell(cell);
      if (indices.length > 0) {
        return indices.map(function (index) {
          const element = self.elements[index];
          return mxUtils.htmlEntities(element.display || (element.object_type + ':' + element.object_id)) +
            '<br><small>' + mxUtils.htmlEntities(element.object_type_label) + '</small>';
        }).join('<hr>');
      }
      return getTooltipForCell.apply(this, arguments);
    };

    // Applies the cursor to cells already rendered.
    graph.refresh();
  };

  PlanDrawingViewer.prototype.installListHooks = function () {
    const self = this;

    this.rows.forEach(function (row) {
      const index = parseInt(row.dataset.index, 10);
      row.addEventListener('click', function (evt) {
        if (evt.target.closest('a, .plan-drawing-element-contents')) {
          return;
        }
        self.select([index], { switchPage: true, scrollDrawing: true });
      });
      row.addEventListener('keydown', function (evt) {
        if (evt.target === row && (evt.key === 'Enter' || evt.key === ' ')) {
          evt.preventDefault();
          self.select([index], { switchPage: true, scrollDrawing: true });
        }
      });
      row.addEventListener('mouseenter', function () {
        self.hover(index);
      });
      row.addEventListener('mouseleave', function () {
        self.hover(null);
      });
    });

    // The objects in a location or rack that are linked in the drawing as well select their
    // elements, and keep the location or rack expanded.
    this.nodes.forEach(function (node) {
      const type = node.dataset.objectType;
      const id = parseInt(node.dataset.objectId, 10);
      const row = parseInt(node.closest('.plan-drawing-element').dataset.index, 10);
      node.indices = [];
      self.elements.forEach(function (element, index) {
        if (element.object_type === type && element.object_id === id) {
          node.indices.push(index);
        }
      });
      const select = function () {
        self.select(node.indices, { switchPage: true, scrollDrawing: true, expand: row });
      };
      node.addEventListener('click', function (evt) {
        if (!evt.target.closest('a')) {
          select();
        }
      });
      node.addEventListener('keydown', function (evt) {
        if (evt.target === node && (evt.key === 'Enter' || evt.key === ' ')) {
          evt.preventDefault();
          select();
        }
      });
      node.addEventListener('mouseenter', function () {
        self.hover(node.indices);
      });
      node.addEventListener('mouseleave', function () {
        self.hover(row);
      });
    });

    const search = document.getElementById('plan-drawing-search');
    if (search) {
      search.addEventListener('input', function () {
        self.search(search.value);
      });
    }

    const pageFilter = document.getElementById('plan-drawing-page-filter');
    if (pageFilter && this.multiPage) {
      pageFilter.hidden = false;
      pageFilter.addEventListener('change', function (evt) {
        self.pageFilter = evt.target.value;
        self.updateList();
      });
    }
  };

  PlanDrawingViewer.prototype.addHighlight = function (cell, color, width) {
    const state = this.graph.view.getState(cell);
    if (!state) {
      return null;
    }
    const highlight = new mxCellHighlight(this.graph, color, width);
    highlight.highlight(state);
    return highlight;
  };

  PlanDrawingViewer.prototype.clearHighlights = function () {
    this.highlights.forEach(function (highlight) {
      highlight.destroy();
    });
    this.highlights = [];
  };

  /** Redraws the highlights for the selected and matching elements on the current page. */
  PlanDrawingViewer.prototype.refreshHighlights = function () {
    const self = this;
    this.clearHighlights();
    this.matches.forEach(function (index) {
      const cell = self.cellForElement(index);
      if (cell && self.selected.indexOf(index) < 0) {
        const highlight = self.addHighlight(cell, MATCH_COLOR, 3);
        if (highlight) {
          self.highlights.push(highlight);
        }
      }
    });
    this.selected.forEach(function (index) {
      const cell = self.cellForElement(index);
      if (cell) {
        const highlight = self.addHighlight(cell, SELECT_COLOR, 4);
        if (highlight) {
          self.highlights.push(highlight);
        }
      }
    });
  };

  PlanDrawingViewer.prototype.select = function (indices, options) {
    options = options || {};
    this.selected = indices;

    if (options.switchPage && indices.length > 0) {
      this.selectPageById(this.elements[indices[0]].page_id);
    }
    this.refreshHighlights();

    this.rows.forEach(function (row) {
      const index = parseInt(row.dataset.index, 10);
      row.classList.toggle('active', indices.indexOf(index) >= 0);
      row.classList.toggle('plan-drawing-expanded', index === options.expand);
    });
    this.nodes.forEach(function (node) {
      node.classList.toggle('active', node.indices.some(function (index) {
        return indices.indexOf(index) >= 0;
      }));
    });

    if (options.scrollList && indices.length > 0) {
      const row = this.rows[indices[0]];
      if (row) {
        row.scrollIntoView({ block: 'nearest' });
      }
    }
    if (options.scrollDrawing && indices.length > 0) {
      const cell = this.cellForElement(indices[0]);
      if (cell) {
        this.graph.scrollCellToVisible(cell, false);
      }
      this.container.scrollIntoView({ block: 'nearest' });
    }
  };

  /** Highlights the elements with the given index or indices on the current page. */
  PlanDrawingViewer.prototype.hover = function (indices) {
    const self = this;
    this.hoverHighlights.forEach(function (highlight) {
      highlight.destroy();
    });
    this.hoverHighlights = [];
    [].concat(indices == null ? [] : indices).forEach(function (index) {
      const cell = self.cellForElement(index);
      const highlight = cell && self.addHighlight(cell, HOVER_COLOR, 3);
      if (highlight) {
        self.hoverHighlights.push(highlight);
      }
    });
  };

  PlanDrawingViewer.prototype.matchesSearch = function (element) {
    const text = [element.display, element.label, element.object_type, element.object_type_label]
      .join(' ').toLowerCase();
    return this.searchTerms.every(function (term) {
      return text.indexOf(term) >= 0;
    });
  };

  /** Shows the elements matching the search, on the current page or on all pages. */
  PlanDrawingViewer.prototype.updateList = function () {
    const self = this;
    const pageId = this.currentPageId();
    const thisPage = this.pageFilter === 'page' && this.multiPage;
    let visible = 0;

    this.rows.forEach(function (row) {
      const element = self.elements[parseInt(row.dataset.index, 10)];
      const show = self.matchesSearch(element) && (!thisPage || element.page_id === pageId);
      row.classList.toggle('d-none', !show);
      if (show) {
        visible++;
      }
    });

    const list = document.getElementById('plan-drawing-elements');
    list.classList.toggle('plan-drawing-this-page', thisPage);
    document.getElementById('plan-drawing-elements-count').textContent = visible;
    const none = document.getElementById('plan-drawing-elements-none');
    none.hidden = visible > 0 || this.rows.length === 0;
    if (this.searchTerms.length > 0) {
      none.textContent = thisPage ? 'No matching elements on this page.' : 'No matching elements.';
    } else {
      none.textContent = 'No elements on this page are linked to NetBox objects.';
    }
  };

  /** Filters the element list, and highlights all elements matching the query. */
  PlanDrawingViewer.prototype.search = function (query) {
    const self = this;
    this.searchTerms = query.toLowerCase().split(/\s+/).filter(Boolean);
    this.matches = [];
    if (this.searchTerms.length > 0) {
      this.elements.forEach(function (element, index) {
        if (self.matchesSearch(element)) {
          self.matches.push(index);
        }
      });
    }

    // Show the first page with matches, unless the current page has some.
    const pageId = this.currentPageId();
    const onPage = this.matches.some(function (index) {
      return self.elements[index].page_id === pageId;
    });
    if (!onPage && this.matches.length > 0) {
      this.selectPageById(this.elements[this.matches[0]].page_id);
    }
    this.updateList();
    this.refreshHighlights();
  };

  /** Selects the elements linked to the object given as '<app_label>.<model>:<id>'. */
  PlanDrawingViewer.prototype.highlightObject = function (key) {
    const parts = key.split(':');
    if (parts.length !== 2) {
      return;
    }
    const type = parts[0].toLowerCase();
    const id = parseInt(parts[1], 10);
    const indices = [];
    this.elements.forEach(function (element, index) {
      if (element.object_type === type && element.object_id === id) {
        indices.push(index);
      }
    });
    this.select(indices, { switchPage: true, scrollDrawing: true, scrollList: true });
  };

  function init() {
    const container = document.getElementById('plan-drawing-viewer');
    const content = readJson('plan-drawing-content');
    if (!container || !content) {
      return;
    }
    const elements = readJson('plan-drawing-elements-data');
    const highlight = readJson('plan-drawing-highlight');

    loadScript(script.dataset.drawioViewer).then(function () {
      const viewer = new PlanDrawingViewer(container, content, elements);
      window.planDrawingViewer = viewer;
      if (highlight) {
        viewer.highlightObject(highlight);
      }
    }).catch(function (e) {
      console.error('Failed to load the draw.io viewer', e);
      container.textContent = 'The draw.io viewer could not be loaded.';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
