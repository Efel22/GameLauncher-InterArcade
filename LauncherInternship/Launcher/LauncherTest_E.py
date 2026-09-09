import sys
import json
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QRect, QSize, QEvent
from PySide6.QtGui import QPixmap, QPainter, QMouseEvent, QFontDatabase, QLinearGradient, QImage
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QLinearGradient,
    QImage,
    QColor
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QMessageBox,
    QLayout,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

BG_PATH = (BASE_DIR / "../assets/images/launcher/bg_interbayamon.png").resolve()
LOGO_PATH = (BASE_DIR / "../assets/images/launcher/name_interbayamon.png").resolve()
TIGER_PATH = (BASE_DIR / "../assets/images/launcher/tiger_interbayamon.png").resolve()

FONT_PATH = BASE_DIR / "../assets/font/Pixelify_Sans/static/PixelifySans-Medium.ttf"

GAMES_FILE = BASE_DIR / "games.json"

BACKGROUND_ZOOM = 1.0


# ============================================================
# FLOW LAYOUT
# ============================================================

class FlowLayout(QLayout):

    def __init__(self, parent=None, margin=0, spacing=20):
        super().__init__(parent)

        self.itemList = []
        self.setSpacing(spacing)

        if parent is not None:
            self.setContentsMargins(
                margin,
                margin,
                margin,
                margin
            )


    def addItem(self, item):
        self.itemList.append(item)


    def count(self):
        return len(self.itemList)


    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]

        return None


    def takeAt(self, index):

        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)

        return None


    def expandingDirections(self):
        return Qt.Orientations(
            Qt.Orientation(0)
        )


    def hasHeightForWidth(self):
        return True


    def heightForWidth(self, width):
        return self.doLayout(
            QRect(0, 0, width, 0),
            True
        )


    def setGeometry(self, rect):
        super().setGeometry(rect)

        self.doLayout(
            rect,
            False
        )


    def sizeHint(self):
        return self.minimumSize()


    def minimumSize(self):

        size = QSize(0, 0)

        for item in self.itemList:

            size = size.expandedTo(
                item.minimumSize()
            )

        margins = self.contentsMargins()

        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom()
        )

        return size


    def doLayout(self, rect, testOnly):

        margins = self.contentsMargins()

        effectiveRect = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom()
        )

        x = effectiveRect.x()
        y = effectiveRect.y()

        lineHeight = 0

        # ----------------------------------------------------
        # First determine rows
        # ----------------------------------------------------

        rows = []
        currentRow = []
        currentWidth = 0

        for item in self.itemList:

            itemSize = item.sizeHint()

            nextWidth = (
                itemSize.width()
                if not currentRow
                else currentWidth + self.spacing() + itemSize.width()
            )

            if (
                currentRow
                and nextWidth > effectiveRect.width()
            ):

                rows.append(currentRow)

                currentRow = [item]
                currentWidth = itemSize.width()

            else:

                currentRow.append(item)
                currentWidth = nextWidth

        if currentRow:
            rows.append(currentRow)


        # ----------------------------------------------------
        # Position rows
        # ----------------------------------------------------

        for row in rows:

            rowWidth = sum(
                item.sizeHint().width()
                for item in row
            )

            rowWidth += self.spacing() * (len(row) - 1)

            # Center the row
            startX = (
                effectiveRect.x()
                + max(
                    0,
                    (effectiveRect.width() - rowWidth) // 2
                )
            )

            x = startX

            lineHeight = max(
                item.sizeHint().height()
                for item in row
            )

            for item in row:

                itemSize = item.sizeHint()

                if not testOnly:

                    item.setGeometry(
                        QRect(
                            x,
                            y,
                            itemSize.width(),
                            itemSize.height()
                        )
                    )

                x += (
                    itemSize.width()
                    + self.spacing()
                )

            y += (
                lineHeight
                + self.spacing()
            )

        return y + margins.bottom() - rect.y()


# ============================================================
# GAME CARD
# ============================================================

class GameCard(QLabel):

    def __init__(self, game_name, poster_path, exe_path):
        super().__init__()

        self.game_name = game_name
        self.exe_path = exe_path

        # Poster size
        self.setFixedSize(179, 245)

        # Makes the mouse cursor show that it is clickable
        self.setCursor(Qt.PointingHandCursor)

        # Load poster
        poster = Path(poster_path)

        if not poster.is_absolute():
            poster = (BASE_DIR / poster).resolve()

        pixmap = QPixmap(str(poster))

        if not pixmap.isNull():

            pixmap = pixmap.scaled(
                139,
                205,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.setPixmap(pixmap)

        else:
            self.setText("No Poster")

        

        self.setAlignment(Qt.AlignCenter)


    # ========================================================
    # CLICK POSTER
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.launch_game()

        super().mousePressEvent(event)


    # ========================================================
    # LAUNCH GAME
    # ========================================================

    def launch_game(self):

        exe = Path(self.exe_path)

        if not exe.is_absolute():
            exe = (BASE_DIR / exe).resolve()

        if not exe.exists():

            QMessageBox.warning(
                self,
                "Game Not Found",
                f"Could not find:\n\n{exe}"
            )

            return

        try:

            subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent)
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Launch Error",
                f"Could not launch the game:\n\n{e}"
            )



# ============================================================
# GRADIENT BACKGROUND
# ============================================================

class GradientBackground(QFrame):

    def paintEvent(self, event):

        painter = QPainter(self)

        width = self.width()
        height = self.height()

        pixel_size = 10

        small_width = max(1, width // pixel_size)
        small_height = max(1, height // pixel_size)

        image = QImage(
            small_width,
            small_height,
            QImage.Format_ARGB32
        )

        import random
        random.seed(12345)

        original = QColor("#3E4559")

        for y in range(small_height):

            progress = y / (small_height - 1)

            # Smooth transition from original color to a darker version
            # of the SAME color.
            t = progress ** 1.4

            dark_color = QColor(
                18, 21, 28
            )

            base_r = int(
                original.red() * (1 - t) +
                dark_color.red() * t
            )

            base_g = int(
                original.green() * (1 - t) +
                dark_color.green() * t
            )

            base_b = int(
                original.blue() * (1 - t) +
                dark_color.blue() * t
            )

            for x in range(small_width):

                variation = random.randint(-7, 7)

                r = max(0, min(255, base_r + variation))
                g = max(0, min(255, base_g + variation))
                b = max(0, min(255, base_b + variation))

                image.setPixelColor(
                    x,
                    y,
                    QColor(r, g, b)
                )

        # Add larger irregular pixel clusters
        for i in range(
            int(small_width * small_height * 0.025)
        ):

            x = random.randint(0, small_width - 1)
            y = random.randint(0, small_height - 1)

            cluster_size = random.randint(1, 4)
            brightness = random.randint(-12, 12)

            for cy in range(cluster_size):

                for cx in range(cluster_size):

                    px = x + cx
                    py = y + cy

                    if px < small_width and py < small_height:

                        current = image.pixelColor(px, py)

                        r = max(
                            0,
                            min(255, current.red() + brightness)
                        )

                        g = max(
                            0,
                            min(255, current.green() + brightness)
                        )

                        b = max(
                            0,
                            min(255, current.blue() + brightness)
                        )

                        image.setPixelColor(
                            px,
                            py,
                            QColor(r, g, b)
                        )

        # Scale the pixel-art pattern back up
        image = image.scaled(
            width,
            height,
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation
        )

        painter.drawImage(
            0,
            0,
            image
        )
# ============================================================
# LAUNCHER
# ============================================================

class Launcher(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Inter-Arcade Games"
        )

        self.setMinimumSize(
            1000,
            700
        )

        self.setup_ui()


    # ========================================================
    # BACKGROUND
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        background = QPixmap(
            str(BG_PATH)
        )

        if background.isNull():

            painter.fillRect(
                self.rect(),
                Qt.GlobalColor.darkGray
            )

            return


        # poster entire window
        scaled = background.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )


        # Zoom
        zoomed = scaled.scaled(
            int(
                scaled.width()
                * BACKGROUND_ZOOM
            ),
            int(
                scaled.height()
                * BACKGROUND_ZOOM
            ),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )


        # Center
        x = (
            self.width()
            - zoomed.width()
        ) // 2

        y = (
            self.height()
            - zoomed.height()
        ) // 2


        painter.drawPixmap(
            x,
            y,
            zoomed
        )


    

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )


        # ====================================================
        # HEADER
        # ====================================================

        header = QFrame()

        header.setFixedHeight(
            80
        )

        header.setStyleSheet("""
            QFrame {
                background-color: #3E4559;
            }
        """)


        header_layout = QVBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            15,
            5,
            15,
            5
        )


        title = QLabel(
            "Inter Arcade Games"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setStyleSheet("""
            QLabel {
                color: white;
                font-family: "Pixelify Sans";
                font-size: 46px;
                font-weight: bold;
            }
        """)


        # Logo
        logo = QLabel()

        logo_pixmap = QPixmap(
            str(LOGO_PATH)
        )

        if not logo_pixmap.isNull():

            logo_pixmap = logo_pixmap.scaled(
                220,
                65,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            logo.setPixmap(
                logo_pixmap
            )

        logo.setAlignment(
            Qt.AlignLeft |
            Qt.AlignVCenter
        )


        # Put logo and title together
        from PySide6.QtWidgets import QHBoxLayout

        header_row = QHBoxLayout()

        header_row.addWidget(
            logo
        )

        header_row.addStretch()

        header_row.addWidget(
            title
        )

        header_row.addStretch()


        # Balance the right side
        header_row.addSpacing(
            220
        )

        header_layout.addLayout(
            header_row
        )

        main_layout.addWidget(
            header
        )


        # ====================================================
        # TIGER
        # ====================================================

        tiger_area = QFrame()

        tiger_area.setFixedHeight(
            140
        )


        tiger_layout = QVBoxLayout(
            tiger_area
        )

        tiger_layout.setContentsMargins(
            10,
            0,
            20,
            0
        )

        tiger_layout.setAlignment(
            Qt.AlignRight |
            Qt.AlignBottom
        )


        tiger = QLabel()

        tiger_pixmap = QPixmap(
            str(TIGER_PATH)
        )

        if not tiger_pixmap.isNull():

            tiger_pixmap = tiger_pixmap.scaled(
                180,
                135,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            tiger.setPixmap(
                tiger_pixmap
            )


        tiger_layout.addWidget(
            tiger,
            alignment=
                Qt.AlignRight |
                Qt.AlignBottom
        )


        main_layout.addWidget(
            tiger_area
        )


        # ====================================================
        # YELLOW BAR
        # ====================================================
        yellow_bar = QFrame()

        yellow_bar.setFixedHeight(42)

        yellow_bar.setStyleSheet("""
            QFrame {
                background-color: #018445;
            }
        """)

        yellow_layout = QVBoxLayout(yellow_bar)

        yellow_layout.setContentsMargins(0, 0, 0, 0)

        game_on = QLabel("Game on!")

        game_on.setAlignment(
            Qt.AlignCenter
        )

        game_on.setStyleSheet("""
            QLabel {
                color: white;
                font-family: "Pixelify Sans";
                font-size: 40px;
                font-weight: bold;
                background: transparent;
            }
        """)

        yellow_layout.addWidget(game_on)

        main_layout.addWidget(yellow_bar)


        # ====================================================
        # GAME AREA
        # ====================================================

        games_background = GradientBackground()

        games_layout = FlowLayout(
            games_background,
            margin=25,
            spacing=20
        )

        games_background.setLayout(
            games_layout
        )

        main_layout.addWidget(
            games_background
        )

        games_background = QFrame()

        games_background.setStyleSheet("""
            QFrame {
                background-color: #3E4559;
            }
        """)


        # Load games
        self.load_games(
            games_layout
        )


    # ========================================================
    # LOAD GAMES
    # ========================================================

    def load_games(self, layout):

        if not GAMES_FILE.exists():

            print(
                "games.json not found."
            )

            return


        try:

            with open(
                GAMES_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                games = json.load(file)


        except Exception as e:

            print(
                f"Could not load games.json: {e}"
            )

            return


        for game in games:

            card = GameCard(
                game["name"],
                game["poster"],
                game["exe"]
            )

            layout.addWidget(
                card
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    # Load Pixelify Sans
    font_id = QFontDatabase.addApplicationFont(
        str(FONT_PATH)
    )

    if font_id == -1:
        print("Could not load Pixelify Sans font.")
    else:
        print("Pixelify Sans loaded successfully.")

    window = Launcher()

    window.show()

    sys.exit(
        app.exec()
    )