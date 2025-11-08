(() => {
    if (window.__smartRecorderAttached) return;
    window.__smartRecorderAttached = true;

    console.log("CrawlRec Attached.");

    // Helper to clean class names for stability  
    const BAD_CLASS_PATTERNS = [
        /^sc-|^css-|^chakra-|^Mui-|^ant-|^__[A-Za-z0-9_-]+$|^BasePopover_|^Styled/,
    ];

    function cleanClassName(c) {
        return c && !BAD_CLASS_PATTERNS.some(rx => rx.test(c));
    }

    // Get stable attributes for elements  
    function getStableAttr(el) {
        const attrs = {};
        for (const a of el.attributes || []) {
            if (
                a.name.startsWith("data-") ||
                a.name.startsWith("aria-") ||
                ["id", "role", "name"].includes(a.name)
            ) {
                attrs[a.name] = a.value;
            }
        }
        return Object.keys(attrs).length ? attrs : null;
    }

    // Builds a stable, reliable selector  
    function buildSelector(el) {
        const parts = [];
        let current = el;
        let depth = 0;

        while (current && current.nodeType === 1 && depth < 6) {
            let part = current.tagName.toLowerCase();

            // Prefer ID if available
            if (current.id && !/^[0-9_\-]+$/.test(current.id)) {
                part += "#" + CSS.escape(current.id);
                parts.unshift(part);
                break;
            }

            // Use data-* or aria-* attribute if unique in the DOM
            const stable = getStableAttr(current);
            if (stable) {
                for (const [k, v] of Object.entries(stable)) {
                    try {
                        const escaped = CSS.escape(v);
                        const query = `${part}[${k}="${escaped}"]`;
                        if (document.querySelectorAll(query).length === 1) {
                            part = query;
                            break;
                        }
                    } catch {}
                }
            } else {
                // Otherwise fallback to cleaned class names
                const cls = Array.from(current.classList || [])
                    .filter(cleanClassName)
                    .slice(0, 2)
                    .map(c => CSS.escape(c))
                    .join(".");
                if (cls) part += "." + cls;
            }

            // Use :nth-of-type for repeated siblings
            const siblings = Array.from(current.parentElement?.children || []).filter(
                e => e.tagName === current.tagName
            );
            if (siblings.length > 1) {
                const index = siblings.indexOf(current) + 1;
                part += `:nth-of-type(${index})`;
            }

            parts.unshift(part);
            current = current.parentElement;
            depth++;
        }

        return parts.join(" > ");
    }

    // Extract element type based on tag  
    function inferExtractType(el) {
        if (el.tagName === "A") return "href";
        if (el.tagName === "IMG") return "src";
        if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") return "value";
        if (el.innerText && el.innerText.trim().length < 200) return "text";
        return "html";
    }

    // Safe text extraction  
    function getText(el) {
        return (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ");
    }

    // Fallback to text-based div search  
    function getClosestDivWithText(el, searchText) {
        const divs = el.closest("div");
        return Array.from(divs.querySelectorAll("div")).find(div =>
            div.innerText && div.innerText.includes(searchText)
        );
    }

    // Fallback mechanism: search for text-based divs if selector fails  
    function getNearbyWords(el, searchText) {
        const parentDiv = el.closest('div');
        const nearbyDivs = parentDiv.querySelectorAll('div');
        return Array.from(nearbyDivs).find(div => {
            return div.innerText.includes(searchText);
        });
    }

    // Core event handler for clicks  
    document.addEventListener(
        "click",
        (event) => {
            if (event.button !== 0 || event.metaKey || event.ctrlKey) return;
            event.preventDefault();
            event.stopPropagation();

            const el = event.target.closest("*");
            if (!el) return;

            // Build both CSS and XPath selectors
            const selector = buildSelector(el);
            const xpathSelector = buildXPath(el);
            const extractType = inferExtractType(el);
            const stableAttrs = getStableAttr(el);

            // Find the closest div by text proximity
            const closestDiv = getClosestDivWithText(el, getText(el));
            const closestDivSelector = closestDiv ? buildSelector(closestDiv) : null;

            // Fallback using nearby words search
            const nearbyDiv = getNearbyWords(el, "Volume");
            const nearbyDivSelector = nearbyDiv ? buildSelector(nearbyDiv) : null;

            // Create information object to send to Python
            const info = {
                selector,
                xpathSelector,  // Save XPath selector as well
                closestDivSelector,
                nearbyDivSelector, // Nearby div with relevant text
                tag: el.tagName.toLowerCase(),
                extractType,
                text: getText(el).slice(0, 150),
                href: el.href || null,
                src: el.src || null,
                value: el.value || null,
                stableAttrs,
                parentSelector: el.parentElement ? buildSelector(el.parentElement) : null,
                timestamp: Date.now(),
            };

            console.log("Captured:", info);

            // Pass data to Python (via exposed method)
            if (window.recordClick) {
                try {
                    window.recordClick(info);
                } catch (e) {
                    console.error("recordClick failed:", e);
                }
            }
        },
        true
    );

    // Function to build full XPath  
    function buildXPath(el) {
        let path = [];
        while (el && el.nodeType === 1) { // 1 is for ELEMENT_NODE
            let index = 1;
            let sibling = el.previousElementSibling;
            while (sibling) {
                if (sibling.tagName === el.tagName) index++;
                sibling = sibling.previousElementSibling;
            }
            let tag = el.tagName.toLowerCase();
            let pathSegment = `${tag}[${index}]`;
            if (el.id) {
                pathSegment = `${tag}[@id="${el.id}"]`;
            }
            path.unshift(pathSegment);
            el = el.parentElement;
        }
        return path.length ? '/' + path.join('/') : null;
    }
})();
