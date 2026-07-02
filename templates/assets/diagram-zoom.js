(function () {
  "use strict";

  const MIN_SCALE = 0.2;
  const MAX_SCALE = 8;
  const ZOOM_STEP = 1.2;

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function initDiagramZoom() {
    if (document.body.dataset.diagramZoomReady === "true") {
      return;
    }
    document.body.dataset.diagramZoomReady = "true";
    document.body.addEventListener("click", (event) => {
      const button = event.target.closest?.(".diagram-zoom-btn");
      if (!button) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const wrapper = button.closest(".diagram-wrap");
      const sourceSvg = wrapper ? wrapper.querySelector("svg") : null;
      if (!sourceSvg) {
        return;
      }
      openZoomOverlay(sourceSvg, button);
    });
  }

  function openZoomOverlay(sourceSvg, triggerButton) {
    const existing = document.querySelector(".diagram-zoom-overlay");
    if (existing && typeof existing.closeDiagramZoom === "function") {
      existing.closeDiagramZoom();
    }

    const originalParent = sourceSvg.parentNode;
    const placeholder = document.createComment("diagram zoom placeholder");
    originalParent.insertBefore(placeholder, sourceSvg);
    const originalSvgAttrs = {
      width: sourceSvg.getAttribute("width"),
      height: sourceSvg.getAttribute("height"),
      style: sourceSvg.getAttribute("style"),
    };
    const svgBox = sourceSvg.viewBox?.baseVal;
    if (svgBox && svgBox.width > 0 && svgBox.height > 0) {
      sourceSvg.setAttribute("width", String(svgBox.width));
      sourceSvg.setAttribute("height", String(svgBox.height));
    }

    const overlay = document.createElement("div");
    overlay.className = "diagram-zoom-overlay is-open";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Diagram zoom");

    const viewport = document.createElement("div");
    viewport.className = "zoom-viewport";

    const container = document.createElement("div");
    container.className = "zoom-container";
    container.appendChild(sourceSvg);
    viewport.appendChild(container);

    const toolbar = document.createElement("div");
    toolbar.className = "zoom-toolbar";
    toolbar.innerHTML = [
      '<button type="button" data-zoom="in" aria-label="Zoom in">+</button>',
      '<button type="button" data-zoom="out" aria-label="Zoom out">-</button>',
      '<button type="button" data-zoom="reset" aria-label="Reset zoom">reset</button>',
      '<button type="button" data-zoom="close" aria-label="Close">x</button>',
    ].join("");

    overlay.appendChild(viewport);
    overlay.appendChild(toolbar);
    document.body.appendChild(overlay);
    document.body.classList.add("zoom-open");

    let scale = 1;
    let tx = 0;
    let ty = 0;
    let dragging = false;
    let activeDragType = "";
    let movedDuringDrag = false;
    let suppressNextClick = false;
    let lastDownPoint = null;
    let lastX = 0;
    let lastY = 0;

    function applyTransform() {
      container.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    }

    function zoomAt(nextScale, x, y) {
      const next = clamp(nextScale, MIN_SCALE, MAX_SCALE);
      const beforeX = (x - tx) / scale;
      const beforeY = (y - ty) / scale;
      scale = next;
      tx = x - beforeX * scale;
      ty = y - beforeY * scale;
      applyTransform();
    }

    function panBy(deltaX, deltaY) {
      tx -= deltaX;
      ty -= deltaY;
      applyTransform();
    }

    function resetZoom() {
      const viewportRect = viewport.getBoundingClientRect();
      const svgRect = sourceSvg.getBoundingClientRect();
      const width = svgRect.width || sourceSvg.viewBox.baseVal.width || viewportRect.width;
      const height = svgRect.height || sourceSvg.viewBox.baseVal.height || viewportRect.height;
      scale = clamp(Math.min((viewportRect.width * 0.86) / width, (viewportRect.height * 0.78) / height, 1.5), MIN_SCALE, MAX_SCALE);
      tx = (viewportRect.width - width * scale) / 2;
      ty = (viewportRect.height - height * scale) / 2;
      applyTransform();
    }

    function closeOverlay() {
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("selectionchange", stopGlobalEvent, true);
      document.body.classList.remove("zoom-open");
      if (placeholder.parentNode) {
        placeholder.parentNode.insertBefore(sourceSvg, placeholder);
        restoreAttribute(sourceSvg, "width", originalSvgAttrs.width);
        restoreAttribute(sourceSvg, "height", originalSvgAttrs.height);
        restoreAttribute(sourceSvg, "style", originalSvgAttrs.style);
        placeholder.remove();
      }
      overlay.remove();
      if (triggerButton && typeof triggerButton.focus === "function") {
        triggerButton.focus();
      }
    }

    function restoreAttribute(node, name, value) {
      if (value === null) {
        node.removeAttribute(name);
      } else {
        node.setAttribute(name, value);
      }
    }

    function stopGlobalEvent(event) {
      event.stopPropagation();
    }

    function onKeyDown(event) {
      if (!document.body.classList.contains("zoom-open")) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeOverlay();
        return;
      }
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        event.stopImmediatePropagation();
        const rect = viewport.getBoundingClientRect();
        zoomAt(scale * ZOOM_STEP, rect.width / 2, rect.height / 2);
        return;
      }
      if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        event.stopImmediatePropagation();
        const rect = viewport.getBoundingClientRect();
        zoomAt(scale / ZOOM_STEP, rect.width / 2, rect.height / 2);
        return;
      }
      if (event.key === "0") {
        event.preventDefault();
        event.stopImmediatePropagation();
        resetZoom();
      }
    }

    overlay.closeDiagramZoom = closeOverlay;

    function recordDownPoint(event) {
      if (event.target.closest?.(".zoom-toolbar")) {
        lastDownPoint = null;
        return;
      }
      lastDownPoint = { x: event.clientX, y: event.clientY };
    }

    overlay.addEventListener("click", (event) => {
      event.stopPropagation();
      const action = event.target.closest?.("[data-zoom]")?.getAttribute("data-zoom");
      const movedFromDown = lastDownPoint
        ? Math.abs(event.clientX - lastDownPoint.x) + Math.abs(event.clientY - lastDownPoint.y) > 4
        : false;
      if (action === "close") {
        closeOverlay();
      } else if (action === "in") {
        const rect = viewport.getBoundingClientRect();
        zoomAt(scale * ZOOM_STEP, rect.width / 2, rect.height / 2);
      } else if (action === "out") {
        const rect = viewport.getBoundingClientRect();
        zoomAt(scale / ZOOM_STEP, rect.width / 2, rect.height / 2);
      } else if (action === "reset") {
        resetZoom();
      } else if ((event.target === overlay || event.target === viewport) && !suppressNextClick && !movedFromDown) {
        closeOverlay();
      }
      suppressNextClick = false;
      lastDownPoint = null;
    });

    overlay.addEventListener("pointerdown", recordDownPoint, true);
    overlay.addEventListener("mousedown", recordDownPoint, true);

    viewport.addEventListener("wheel", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (event.ctrlKey || event.metaKey) {
        const rect = viewport.getBoundingClientRect();
        const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
        zoomAt(scale * factor, event.clientX - rect.left, event.clientY - rect.top);
      } else {
        panBy(event.deltaX, event.deltaY);
      }
    }, { passive: false });

    function beginDrag(event) {
      if (activeDragType) {
        return;
      }
      if (event.target.closest?.(".zoom-toolbar")) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      activeDragType = event.type.startsWith("pointer") ? "pointer" : "mouse";
      movedDuringDrag = false;
      suppressNextClick = event.target !== viewport && event.target !== overlay;
      lastX = event.clientX;
      lastY = event.clientY;
      if (activeDragType === "pointer") {
        viewport.setPointerCapture?.(event.pointerId);
      }
    }

    function updateDrag(event) {
      const eventType = event.type.startsWith("pointer") ? "pointer" : "mouse";
      if (!activeDragType || eventType !== activeDragType) {
        return;
      }
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      if (!dragging && Math.abs(dx) + Math.abs(dy) <= 2) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (!dragging) {
        dragging = true;
        movedDuringDrag = true;
        suppressNextClick = true;
        container.classList.add("is-dragging");
      }
      tx += dx;
      ty += dy;
      lastX = event.clientX;
      lastY = event.clientY;
      applyTransform();
    }

    function endDrag(event) {
      const eventType = event.type.startsWith("pointer") ? "pointer" : "mouse";
      if (!activeDragType || eventType !== activeDragType) {
        return;
      }
      const wasDragging = dragging;
      if (wasDragging) {
        event.preventDefault();
        event.stopPropagation();
      }
      dragging = false;
      activeDragType = "";
      suppressNextClick = suppressNextClick || movedDuringDrag;
      movedDuringDrag = false;
      container.classList.remove("is-dragging");
      if (eventType === "pointer") {
        viewport.releasePointerCapture?.(event.pointerId);
      }
    }

    function cancelDrag() {
      if (activeDragType && dragging) {
        suppressNextClick = true;
      }
      dragging = false;
      activeDragType = "";
      movedDuringDrag = false;
      container.classList.remove("is-dragging");
    }

    viewport.addEventListener("pointerdown", beginDrag);
    viewport.addEventListener("pointermove", updateDrag);
    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", cancelDrag);
    viewport.addEventListener("pointerleave", cancelDrag);
    viewport.addEventListener("mousedown", beginDrag);
    viewport.addEventListener("mousemove", updateDrag);
    viewport.addEventListener("mouseup", endDrag);
    viewport.addEventListener("mouseleave", cancelDrag);

    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("selectionchange", stopGlobalEvent, true);
    window.requestAnimationFrame(resetZoom);
    const closeButton = toolbar.querySelector('[data-zoom="close"]');
    closeButton?.focus();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDiagramZoom);
  } else {
    initDiagramZoom();
  }

  window.initDiagramZoom = initDiagramZoom;
  window.openZoomOverlay = openZoomOverlay;
})();
