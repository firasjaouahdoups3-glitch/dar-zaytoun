/**
 * Dar Zaytoun — scripts du site (JavaScript natif, sans dépendance)
 * ---------------------------------------------------------------------------
 * Chaque fonctionnalité est isolée dans une fonction init…() appelée en bas
 * du fichier. Toutes vérifient que leurs éléments existent : on peut retirer
 * une section du gabarit sans casser le reste.
 *
 *   1. initNavToggle      menu mobile (ouverture, Échap, fermeture au clic)
 *   2. initHeader         en-tête opaque après défilement
 *   3. initSectionTracking lien actif + sélecteur de langue qui garde la section
 *   4. initReveal         apparition douce des blocs au défilement
 *   5. initLightbox       visionneuse de la galerie (<dialog> natif)
 *   6. initBookingForm    validation du formulaire de réservation
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var isRTL = root.dir === "rtl";
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;


  /* 1. MENU MOBILE ======================================================== */
  function initNavToggle() {
    var toggle = document.querySelector("[data-nav-toggle]");
    var nav = document.querySelector("[data-nav]");
    if (!toggle || !nav) return;

    var label = toggle.querySelector("[data-nav-toggle-label]");

    function setOpen(open) {
      toggle.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
      label.textContent = open ? toggle.dataset.labelClose : toggle.dataset.labelOpen;
    }

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    // Un clic sur un lien du menu le referme (la page défile vers la section)
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setOpen(false);
    });

    // Échap referme le menu et rend le focus au bouton
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });

    // Si l'écran s'élargit (rotation, redimensionnement), on remet à zéro
    window.matchMedia("(min-width: 64rem)").addEventListener("change", function (e) {
      if (e.matches) setOpen(false);
    });
  }


  /* 2. EN-TÊTE ============================================================ */
  function initHeader() {
    var header = document.querySelector("[data-header]");
    if (!header) return;

    var ticking = false;
    function update() {
      header.classList.toggle("is-scrolled", window.scrollY > 24);
      ticking = false;
    }
    // requestAnimationFrame : au plus une mise à jour par image affichée
    window.addEventListener("scroll", function () {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }


  /* 3. SECTION COURANTE & SÉLECTEUR DE LANGUE ============================== */
  /*
   * Un IntersectionObserver repère la section au milieu de l'écran.
   * On s'en sert pour :
   *   - surligner le lien correspondant dans la navigation ;
   *   - réécrire les liens de langue : « ../en/ » devient « ../en/#menu ».
   * Les identifiants de section (#menu, #booking…) étant identiques dans
   * toutes les langues, on arrive au même endroit sur la page traduite.
   */
  function initSectionTracking() {
    var sections = document.querySelectorAll("main section[id]");
    var navLinks = document.querySelectorAll("[data-nav-link]");
    var langLinks = document.querySelectorAll("[data-lang-link]");
    if (!sections.length || !("IntersectionObserver" in window)) return;

    // Adresse de base de chaque lien de langue (sans ancre)
    langLinks.forEach(function (link) {
      link.dataset.baseHref = link.getAttribute("href").split("#")[0];
    });

    function setCurrent(id) {
      navLinks.forEach(function (link) {
        link.classList.toggle("is-active", link.hash === "#" + id);
      });
      langLinks.forEach(function (link) {
        link.href = link.dataset.baseHref + (id && id !== "top" ? "#" + id : "");
      });
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) setCurrent(entry.target.id);
      });
    }, {
      // Zone de détection : une fine bande au milieu de l'écran
      rootMargin: "-45% 0px -50% 0px"
    });

    sections.forEach(function (section) { observer.observe(section); });
    setCurrent(window.location.hash.slice(1));
  }


  /* 4. ANIMATIONS AU DÉFILEMENT =========================================== */
  function initReveal() {
    var items = document.querySelectorAll(".reveal");
    if (!items.length) return;

    // Pas d'animation si l'utilisateur les a désactivées ou si l'API manque
    if (reducedMotion || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }

    // Léger décalage en cascade entre éléments frères (max ~0,4 s)
    items.forEach(function (el) {
      var siblings = Array.prototype.filter.call(el.parentElement.children, function (child) {
        return child.classList.contains("reveal");
      });
      var index = siblings.indexOf(el);
      el.style.setProperty("--reveal-delay", Math.min(index, 4) * 90 + "ms");
    });

    var observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          obs.unobserve(entry.target);   // une seule fois : plus rien à surveiller
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });

    items.forEach(function (el) { observer.observe(el); });
  }


  /* 5. VISIONNEUSE DE LA GALERIE ========================================== */
  /*
   * <dialog> + showModal() offre gratuitement : piège du focus, fermeture
   * par Échap, arrière-plan inerte pour les lecteurs d'écran.
   */
  function initLightbox() {
    var dialog = document.querySelector("[data-lightbox]");
    var triggers = Array.prototype.slice.call(document.querySelectorAll("[data-gallery-src]"));
    if (!dialog || !triggers.length || typeof dialog.showModal !== "function") return;

    var img = dialog.querySelector("[data-lightbox-img]");
    var caption = dialog.querySelector("[data-lightbox-caption]");
    var counter = dialog.querySelector("[data-lightbox-counter]");
    var current = 0;
    var lastTrigger = null;

    function show(index) {
      // Modulo : après la dernière image on revient à la première
      current = (index + triggers.length) % triggers.length;
      var trigger = triggers[current];
      img.src = trigger.dataset.gallerySrc;
      img.alt = trigger.dataset.galleryAlt;
      caption.textContent = trigger.dataset.galleryCaption;
      counter.textContent = (current + 1) + " / " + triggers.length;
    }

    triggers.forEach(function (trigger, index) {
      trigger.addEventListener("click", function () {
        lastTrigger = trigger;
        show(index);
        dialog.showModal();
      });
    });

    dialog.querySelector("[data-lightbox-prev]").addEventListener("click", function () { show(current - 1); });
    dialog.querySelector("[data-lightbox-next]").addEventListener("click", function () { show(current + 1); });
    dialog.querySelector("[data-lightbox-close]").addEventListener("click", function () { dialog.close(); });

    // Flèches du clavier : en arabe, « suivant » est vers la gauche
    dialog.addEventListener("keydown", function (event) {
      if (event.key === "ArrowRight") show(current + (isRTL ? -1 : 1));
      if (event.key === "ArrowLeft") show(current + (isRTL ? 1 : -1));
    });

    // Clic en dehors de l'image (sur le fond) = fermeture
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });

    // À la fermeture, le focus revient sur la vignette d'origine
    dialog.addEventListener("close", function () {
      if (lastTrigger) lastTrigger.focus();
    });
  }


  /* 6. FORMULAIRE DE RÉSERVATION ========================================= */
  /*
   * Tous les messages viennent des attributs data-msg-* du <form>,
   * eux-mêmes générés depuis les fichiers de traduction : aucun texte
   * n'est écrit en dur ici.
   */
  function initBookingForm() {
    var form = document.querySelector("[data-booking-form]");
    if (!form) return;

    var msg = form.dataset;
    var fields = form.elements;
    var status = form.querySelector("[data-form-status]");
    var submit = form.querySelector("[data-submit]");
    var submitLabel = form.querySelector("[data-submit-label]");
    var closedDay = Number(msg.closedDay);
    var today = toISODate(new Date());

    // Interdit de choisir une date passée dans le calendrier natif
    fields.date.min = today;

    /* Chaque règle renvoie "" si le champ est valide, sinon le message. */
    var rules = {
      name: function (v) {
        if (!v) return msg.msgRequired;
        return v.length >= 2 ? "" : msg.msgName;
      },
      email: function (v) {
        if (!v) return msg.msgRequired;
        return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v) ? "" : msg.msgEmail;
      },
      phone: function (v) {
        if (!v) return "";   // facultatif
        return /^\+?[\d\s().-]{6,20}$/.test(v) ? "" : msg.msgPhone;
      },
      date: function (v) {
        if (!v) return msg.msgRequired;
        if (v < today) return msg.msgDatePast;            // comparaison ISO AAAA-MM-JJ
        if (new Date(v + "T12:00").getDay() === closedDay) return msg.msgDateClosed;
        return "";
      },
      time: function (v, input) {
        if (!v) return msg.msgRequired;
        return v >= input.min && v <= input.max ? "" : msg.msgTime;
      },
      guests: function (v, input) {
        var n = Number(v);
        if (!v) return msg.msgRequired;
        return Number.isInteger(n) && n >= Number(input.min) && n <= Number(input.max) ? "" : msg.msgGuests;
      },
      consent: function (v, input) {
        return input.checked ? "" : msg.msgConsent;
      }
    };

    function validateField(input) {
      var rule = rules[input.name];
      if (!rule) return true;
      var error = rule(input.value.trim(), input);
      var errorEl = form.querySelector('[data-error-for="' + input.id + '"]');

      if (error) {
        input.setAttribute("aria-invalid", "true");
      } else {
        input.removeAttribute("aria-invalid");
      }
      if (errorEl) errorEl.textContent = error;
      return !error;
    }

    // Validation « douce » : à la sortie du champ, puis en direct une fois en erreur
    Object.keys(rules).forEach(function (name) {
      var input = fields[name];
      input.addEventListener("blur", function () {
        if (input.value || input.dataset.touched) validateField(input);
        input.dataset.touched = "true";
      });
      input.addEventListener(input.type === "checkbox" ? "change" : "input", function () {
        if (input.getAttribute("aria-invalid") === "true") validateField(input);
      });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();   // pas de serveur : on simule l'envoi
      status.className = "form-status";
      status.textContent = "";

      var invalid = Object.keys(rules)
        .map(function (name) { return fields[name]; })
        .filter(function (input) { return !validateField(input); });

      if (invalid.length) {
        status.classList.add("is-error");
        status.textContent = msg.msgSummary.replace("{count}", invalid.length);
        invalid[0].focus();     // on emmène l'utilisateur au premier problème
        return;
      }

      // Simulation d'un envoi réseau (remplacer par fetch() vers un vrai service)
      submit.disabled = true;
      form.setAttribute("aria-busy", "true");
      var originalLabel = submitLabel.textContent;
      submitLabel.textContent = msg.msgSending;

      window.setTimeout(function () {
        var data = {
          name: fields.name.value.trim(),
          date: formatDate(fields.date.value, msg.locale),
          time: fields.time.value,
          guests: fields.guests.value
        };
        status.classList.add("is-success");
        status.textContent = msg.msgSuccess.replace(/\{(\w+)\}/g, function (_, key) {
          return data[key] || "";
        });

        form.reset();
        Object.keys(rules).forEach(function (name) { delete fields[name].dataset.touched; });
        submit.disabled = false;
        form.removeAttribute("aria-busy");
        submitLabel.textContent = originalLabel;
      }, 900);
    });
  }


  /* -- Petites fonctions utilitaires -------------------------------------- */

  // Date locale -> "AAAA-MM-JJ" (format des <input type="date">)
  function toISODate(d) {
    var pad = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  // "2026-12-04" -> « vendredi 4 décembre 2026 » selon la langue de la page
  function formatDate(iso, locale) {
    try {
      return new Intl.DateTimeFormat(locale, { dateStyle: "full" }).format(new Date(iso + "T12:00"));
    } catch (e) {
      return iso;
    }
  }


  /* Lancement ============================================================== */
  initNavToggle();
  initHeader();
  initSectionTracking();
  initReveal();
  initLightbox();
  initBookingForm();
})();
