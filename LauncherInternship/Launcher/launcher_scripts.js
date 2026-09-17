/* ============================================================
   LOGO MODE

   'image' -> use name_interbayamon.png
   'text'  -> use INTER / BAYAMÓN CSS badges
   ============================================================ */

const LOGO_MODE = "image";

/*
   Path to the cartridge frame artwork used behind every poster.
*/

const CARTRIDGE_IMAGE = "assets/images/launcher/stylized_game_cartridge.png";

/*
   Reads the --card-scale CSS variable so JS-driven sizing
   (card height, carousel spacing) stays in sync with the
   CSS-driven sizing (card/poster width) whenever you change
   --card-scale in :root.
*/

function getCardScale() {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(
    "--card-scale",
  );

  const value = parseFloat(raw);

  return Number.isFinite(value) ? value : 1;
}

/*
   The card box (--card-w / --card-h) has to match the real
   width:height ratio of the cartridge artwork, or else
   object-fit stretches/shrinks the frame and the poster slot
   (sized as a % of the card) no longer lines up with it.

   The first time the cartridge image loads, we read its
   natural size and rewrite --card-h to match the card's
   scaled width exactly, so every card is sized to the
   artwork's real proportions at whatever --card-scale is set.
*/

let cartridgeRatioLocked = false;

function lockCartridgeRatio(frameImg) {
  if (cartridgeRatioLocked) {
    return;
  }

  if (!frameImg.naturalWidth || !frameImg.naturalHeight) {
    return;
  }

  cartridgeRatioLocked = true;

  const root = document.documentElement;

  const baseCardW = parseFloat(
    getComputedStyle(root).getPropertyValue("--card-w"),
  );

  const scaledCardW = baseCardW * getCardScale();

  const ratio = frameImg.naturalHeight / frameImg.naturalWidth;

  root.style.setProperty("--card-h", scaledCardW * ratio + "px");
}

/* ============================================================
   GAMES DATA
   ============================================================ */

const GAMES = [
  {
    name: "Locked In Area 51",

    poster: "assets/images/posters/locked_in_area_51.png",

    exe: "../../ArcadeGames/LockedInArea51/TigerGameJam.exe",

    type: "2D Platformer",
  },

  {
    name: "Memories of Ladein",

    poster: "assets/images/posters/memories_of_ladein.png",

    exe: "../../ArcadeGames/MemoriesOfLadein/MemoriesOfLadien_v1.1.3/Project_Fallen_Angel.exe",

    type: "2D Platformer",
  },

  {
    name: "Project Emergency",

    poster: "assets/images/posters/project_emergency.png",

    exe: "../../ArcadeGames/MasterWorkforceProject/Windows/ProyectoEmergencia.exe",

    type: "Survival",
  },

  {
    name: "Vanishing Stars",

    poster: "assets/images/posters/vanishing_stars.png",

    exe: "../../ArcadeGames/VanishingStars/Windows/Vanishing Stars.exe",

    type: "Action",
  },

  {
    name: "Vanishing Stars",

    poster: "assets/images/posters/vanishing_stars.png",

    exe: "../../ArcadeGames/VanishingStars/Windows/Vanishing Stars.exe",

    type: "Action",
  },
];

/* ============================================================
   CAROUSEL STATE
   ============================================================ */

let currentIndex = 0;

/*
   How far apart the cards are horizontally, at --card-scale: 1.
   This scales automatically with --card-scale so cards stay
   proportionally spaced no matter how big you make them.
*/

const BASE_CARD_SPACING = 200;

/*
   How much smaller the side cards become.

   Center card = 1.25
   One card away = 0.82
   Two cards away = 0.65
*/

const CENTER_SCALE = 1.25;

const SIDE_SCALE = 0.82;

const FAR_SCALE = 0.65;

/* ============================================================
   CREATE GAME CARDS
   ============================================================ */

function renderGames(games) {
  const track = document.getElementById("gameGrid");

  const indicators = document.getElementById("carouselIndicators");

  track.innerHTML = "";

  indicators.innerHTML = "";

  games.forEach((game, index) => {
    /*
       Create card wrapper
    */

    const wrap = document.createElement("div");

    wrap.className = "game-card-wrap";

    wrap.dataset.index = index;

    wrap.title = game.name;

    /*
       Create card stage (cartridge frame + poster slot)
    */

    const card = document.createElement("div");

    card.className = "game-card";

    /*
       Cartridge frame artwork, drawn on top so its
       border/shape reads as the "case" around the poster.
    */

    const frame = new Image();

    frame.className = "cartridge-frame";

    frame.alt = "";

    frame.draggable = false;

    frame.addEventListener("load", () => lockCartridgeRatio(frame));

    frame.src = CARTRIDGE_IMAGE;

    /*
       Poster slot: the inset window that holds the
       game's poster art, rounded and padded to sit
       inside the cartridge artwork.
    */

    const slot = document.createElement("div");

    slot.className = "poster-slot";

    const img = new Image();

    img.alt = game.name;

    img.src = game.poster;

    img.draggable = false;

    img.onerror = () => {
      slot.innerHTML = `<div class="no-poster">
          No Poster
          <br>
          ${game.name}
        </div>`;
    };

    slot.appendChild(img);

    card.appendChild(slot);

    card.appendChild(frame);

    /*
       Game title
    */

    const titleEl = document.createElement("div");

    titleEl.className = "game-title";

    titleEl.textContent = game.name;

    /*
       Game type
    */

    const typeEl = document.createElement("div");

    typeEl.className = "game-type";

    typeEl.textContent = game.type || "—";

    /*
       Put everything together
    */

    wrap.appendChild(card);

    wrap.appendChild(titleEl);

    wrap.appendChild(typeEl);

    /*
       Clicking a game:
       
       - If it is already centered -> launch
       - Otherwise -> move it to center
    */

    wrap.addEventListener("click", () => {
      if (index === currentIndex) {
        launchGame(game);
      } else {
        currentIndex = index;

        updateCarousel();
      }
    });

    track.appendChild(wrap);

    /*
       Create indicator dot
    */

    const indicator = document.createElement("button");

    indicator.className = "carousel-indicator";

    indicator.setAttribute("aria-label", `Select ${game.name}`);

    indicator.addEventListener("click", () => {
      currentIndex = index;

      updateCarousel();
    });

    indicators.appendChild(indicator);
  });

  updateCarousel();
}

/* ============================================================
   UPDATE CAROUSEL

   This is the main part that creates the
   Just Dance-style visual layout.
   ============================================================ */

function updateCarousel() {
  const cards = document.querySelectorAll(".game-card-wrap");

  const indicators = document.querySelectorAll(".carousel-indicator");

  const cardSpacing = BASE_CARD_SPACING * getCardScale();

  cards.forEach((card, index) => {
    /*
       Calculate the card's position relative
       to the currently selected game.
    */

    let offset = index - currentIndex;

    /*
       With a small number of games, make the
       carousel wrap around.

       Example:

       Current = 0

       Game 3 becomes the card immediately
       to the left instead of being far away.
    */

    const total = GAMES.length;

    if (offset > total / 2) {
      offset -= total;
    }

    if (offset < -total / 2) {
      offset += total;
    }

    /*
       Horizontal position
    */

    const x = offset * cardSpacing;

    /*
       Scale depending on distance
    */

    let scale = FAR_SCALE;

    if (offset === 0) {
      scale = CENTER_SCALE;
    } else if (Math.abs(offset) === 1) {
      scale = SIDE_SCALE;
    }

    /*
       Cards further away become less visible.
    */

    let opacity = 0.35;

    if (Math.abs(offset) === 1) {
      opacity = 0.72;
    }

    if (offset === 0) {
      opacity = 1;
    }

    /*
       Blur distant cards slightly.

       The center card stays completely sharp.
    */

    let blur = 1.5;

    if (offset === 0) {
      blur = 0;
    }

    /*
       Apply visual state
    */

    card.style.transform = `translate(-50%, -50%) translateX(${x}px) scale(${scale})`;

    card.style.opacity = opacity;

    card.style.filter = `blur(${blur}px)`;

    /*
       Z-index

       Center should always be above side cards.
    */

    card.style.zIndex = 10 - Math.abs(offset);

    /*
       State classes
    */

    card.classList.remove("is-center", "is-side");

    if (offset === 0) {
      card.classList.add("is-center");
    } else {
      card.classList.add("is-side");
    }
  });

  /*
     Update indicator dots
  */

  indicators.forEach((indicator, index) => {
    indicator.classList.toggle("active", index === currentIndex);
  });
}

/* ============================================================
   PREVIOUS GAME
   ============================================================ */

function previousGame() {
  currentIndex--;

  if (currentIndex < 0) {
    currentIndex = GAMES.length - 1;
  }

  updateCarousel();
}

/* ============================================================
   NEXT GAME
   ============================================================ */

function nextGame() {
  currentIndex++;

  if (currentIndex >= GAMES.length) {
    currentIndex = 0;
  }

  updateCarousel();
}

/* ============================================================
   ARROW BUTTONS
   ============================================================ */

document.getElementById("prevButton").addEventListener("click", previousGame);

document.getElementById("nextButton").addEventListener("click", nextGame);

/* ============================================================
   KEYBOARD CONTROLS
   ============================================================ */

document.addEventListener("keydown", (event) => {
  /*
       Do not interfere with typing
       into an input if one is ever added.
    */

  if (event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA") {
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();

    previousGame();
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();

    nextGame();
  }

  /*
       Enter launches the currently
       selected game.
    */

  if (event.key === "Enter") {
    event.preventDefault();

    const game = GAMES[currentIndex];

    if (game) {
      launchGame(game);
    }
  }
});

/* ============================================================
   LAUNCH GAME

   The browser sends the game path to
   launcher_server.py.

   The Python server handles subprocess.Popen().
   ============================================================ */

function launchGame(game) {

  const selectedCard =
    document.querySelector(
      `.game-card-wrap[data-index="${currentIndex}"]`
    );

  if (!selectedCard) {
    return;
  }

  const cartridge =
    selectedCard.querySelector('.cartridge-frame');

  if (!cartridge) {
    return;
  }


  /* ------------------------------------------------------------
     Find the starting position of the cartridge
     ------------------------------------------------------------ */

  const startRect =
    cartridge.getBoundingClientRect();


  /* ------------------------------------------------------------
     Find the cartridge slot
     ------------------------------------------------------------ */

  const slot =
    document.getElementById('cartridge-slot');

  const slotRect =
    slot.getBoundingClientRect();


  /* ------------------------------------------------------------
     Clone the cartridge so the original stays in place
     ------------------------------------------------------------ */

  const flyingCartridge =
    cartridge.cloneNode(true);

  flyingCartridge.classList.add(
    'flying-cartridge'
  );

  document.body.appendChild(
    flyingCartridge
  );


  /* Starting position */

  flyingCartridge.style.left =
    startRect.left + 'px';

  flyingCartridge.style.top =
    startRect.top + 'px';

  flyingCartridge.style.width =
    startRect.width + 'px';

  flyingCartridge.style.height =
    startRect.height + 'px';


  /* Force browser to render starting position */

  flyingCartridge.getBoundingClientRect();


  /* ------------------------------------------------------------
     Animate cartridge into the slot
     ------------------------------------------------------------ */

  const targetWidth =
    startRect.width * 0.45;

  const targetHeight =
    startRect.height * 0.45;

  flyingCartridge.style.left =
    (
      slotRect.left +
      slotRect.width / 2 -
      targetWidth / 2
    ) + 'px';

  flyingCartridge.style.top =
    (
      slotRect.top -
      targetHeight * 0.35
    ) + 'px';

  flyingCartridge.style.width =
    targetWidth + 'px';

  flyingCartridge.style.height =
    targetHeight + 'px';

  flyingCartridge.style.transform =
    'rotate(0deg)';


  /* ------------------------------------------------------------
     After cartridge animation finishes
     ------------------------------------------------------------ */

  setTimeout(() => {

    flyingCartridge.style.transform =
      'translateY(35px)';

    setTimeout(() => {

      flyingCartridge.remove();

      startLoadingScreen(game);

    }, 400);

  }, 900);

}

function startLoadingScreen(game) {

  const loadingScreen =
    document.getElementById('loading-screen');

  const progress =
    document.getElementById('loading-progress');

  const loadingText =
    document.getElementById('loading-text');


  loadingScreen.classList.add('show');

  progress.style.width = '0%';

  let elapsed = 0;

  const totalTime = 15000;

  const interval =
    setInterval(() => {

      elapsed += 100;

      const percent =
        Math.min(
          (elapsed / totalTime) * 100,
          100
        );

      progress.style.width =
        percent + '%';


      /* Change the fake loading messages */

      if (percent < 20) {

        loadingText.textContent =
          'Reading cartridge...';

      } else if (percent < 45) {

        loadingText.textContent =
          'Loading game data...';

      } else if (percent < 70) {

        loadingText.textContent =
          'Preparing game world...';

      } else if (percent < 90) {

        loadingText.textContent =
          'Starting game...';

      } else {

        loadingText.textContent =
          'Almost ready...';

      }


      /* --------------------------------------------------------
         Finished
         -------------------------------------------------------- */

      if (elapsed >= totalTime) {

        clearInterval(interval);

        loadingText.textContent =
          'Launching!';


        /* Actually launch the game */

        fetch('/launch', {

          method: 'POST',

          headers: {
            'Content-Type': 'application/json'
          },

          body: JSON.stringify({
            exe: game.exe
          })

        })

        .then(
          res =>
            res.json().catch(
              () => ({
                ok: false,
                error: `HTTP ${res.status}`
              })
            )
        )

        .then(data => {

          if (data.ok) {

            setTimeout(() => {
              loadingScreen.classList.remove('show');
            }, 500);

          } else {

            loadingText.textContent =
              `Could not launch "${game.name}"`;

            setTimeout(() => {
              loadingScreen.classList.remove('show');
            }, 2000);

          }

        })

        .catch(() => {

          loadingText.textContent =
            'Could not reach launcher server.';

          setTimeout(() => {
            loadingScreen.classList.remove('show');
          }, 2500);

        });

      }

    }, 100);

}

// function launchGame(game) {
//   showToast(`Launching "${game.name}"...`);

//   fetch("/launch", {
//     method: "POST",

//     headers: {
//       "Content-Type": "application/json",
//     },

//     body: JSON.stringify({
//       exe: game.exe,
//     }),
//   })
//     .then((res) =>
//       res.json().catch(() => ({
//         ok: false,
//         error: `HTTP ${res.status}`,
//       })),
//     )

//     .then((data) => {
//       if (data.ok) {
//         showToast(`Launched "${game.name}"`);
//       } else {
//         showToast(
//           `Could not launch "${game.name}": ${data.error || "unknown error"}`,
//         );
//       }
//     })

//     .catch(() => {
//       showToast(
//         `Could not reach launcher_server.py — run it and open this page from there.`,
//       );
//     });
// }

/* ============================================================
   TOAST
   ============================================================ */

let toastTimer = null;

function showToast(message) {
  const toast = document.getElementById("toast");

  toast.textContent = message;

  toast.classList.add("show");

  clearTimeout(toastTimer);

  toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
}

/* ============================================================
   INIT
   ============================================================ */

window.addEventListener("load", () => {
  /*
       Set logo mode
    */

  document.getElementById("app").classList.add("logo-mode-" + LOGO_MODE);

  /*
       Create carousel
    */

  renderGames(GAMES);
});
