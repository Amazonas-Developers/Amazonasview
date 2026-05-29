from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QMouseEvent, QPainter, QBrush, QPen


class Interactive_imageLabel(QLabel):

    point_change = Signal(list,bool, list,bool, list, bool, list, bool)
    door_point_change = Signal(list)
    door_direction_change = Signal(list)


    def __init__(self, parent=None,
                roi=[],
                roi_active=False,
                roi_door=[],
                roi_door_active=False,
                dor_direction=None,
                dor_direction_active=False,
                roi_entrega=[],
                roi_entrega_active=False,
                **kwargs
        ):
        super().__init__(parent)
        self.setMouseTracking(True)
        # Normalizar nombres de entrada para compatibilidad con dicts
        # roi_active puede venir como 'roi_activate'
        roi_active_val = kwargs.get('roi_activate', roi_active)

        # roi_door puede venir como 'door_roi' o 'roi_door'
        roi_door_val = roi_door if roi_door else kwargs.get('door_roi', kwargs.get('roi_door', []))
        roi_door_active_val = roi_door_active or kwargs.get('door_roi_activate', kwargs.get('door_roi_active', False))

        # door direction puede venir como 'door_direction' o 'dor_direction'
        door_direction_val = dor_direction if dor_direction is not None else kwargs.get('door_direction', kwargs.get('dor_direction', []))
        door_direction_active_val = dor_direction_active or kwargs.get('door_direction_active', kwargs.get('dor_direction_active', False))

        # Entrega ROI
        roi_entrega_val = roi_entrega if roi_entrega else kwargs.get('roi_entrega', [])
        roi_entrega_active_val = roi_entrega_active or kwargs.get('roi_entrega_activate', kwargs.get('roi_entrega_active', False))

        # Flag para mostrar/ocultar puntos VISUALMENTE (no afecta si el ROI está activo)
        self.show_points = bool(roi_active_val)
        # Flag separada: los QPoints son editables/interactivos (se pueden arrastrar)
        self.points_editable = True
        # Flag para ocultar solo el dibujo de puntos/líneas sin desactivar el ROI
        self.points_hidden = False

        # Puntos iniciales (0–1000)
        self.points = self.list_to_qpoints(roi)

        # Door ROI y dirección (normalizados)
        self.door_points = self.list_to_qpoints(roi_door_val)
        self.door_active = bool(roi_door_active_val)

        self.door_direction = self.list_to_qpoints(door_direction_val) if door_direction_val is not None else []  # espera 2 puntos
        self.door_direction_active = bool(door_direction_active_val)

        # Entrega ROI (verde)
        self.entrega_points = self.list_to_qpoints(roi_entrega_val)
        self.entrega_active = bool(roi_entrega_active_val)

        # Qué conjunto de puntos estamos editando: 'roi' | 'door' | 'direction' | 'entrega'
        self.edit_target = 'roi'

        self.active_point_index = -1
        self.point_radius = 10
        self.current_pixmap = QPixmap()
        # Respetar el estado inicial de roi_active en lugar de forzar hide
        if not self.show_points:
            self.hide_points()

    # ------------------------------------------------------------
    # CONTROL DE VISIBILIDAD DE PUNTOS
    # ------------------------------------------------------------
    def hide_points(self):
        self.show_points = False
        self.update()

    def show_points_fn(self):
        self.show_points = True
        self.update()

    def toggle_points(self):
        self.show_points = not self.show_points
        self.update()

    def toggle_points_visibility(self):
        """Oculta/muestra el dibujo de puntos y líneas SIN desactivar el ROI."""
        self.points_hidden = not self.points_hidden
        self.update()

    def reset_points(self):
        """Reinicia todos los ROIs a una posicion por defecto visible y arrastrable."""
        # Coordenadas normalizadas 0-1000
        self.points = [QPoint(100, 100), QPoint(900, 100),
                       QPoint(900, 900), QPoint(100, 900)]
        self.door_points = [QPoint(400, 100), QPoint(600, 100),
                            QPoint(600, 300), QPoint(400, 300)]
        self.door_direction = [QPoint(500, 400), QPoint(500, 600)]
        self.entrega_points = [QPoint(400, 700), QPoint(600, 700),
                               QPoint(600, 900), QPoint(400, 900)]
        self.active_point_index = -1
        # Forzar visibilidad de los 4 ROIs para que el usuario los vea inmediatamente
        self.show_points = True
        self.points_hidden = False
        self.door_active = True
        self.door_direction_active = True
        self.entrega_active = True
        self.update()

    def get_reset_lists(self):
        """Devuelve las posiciones por defecto como listas [[x,y], ...] para persistir."""
        return {
            "roi":              [[100, 100], [900, 100], [900, 900], [100, 900]],
            "roi_door":         [[400, 100], [600, 100], [600, 300], [400, 300]],
            "roi_dor_direction":[[500, 400], [500, 600]],
            "roi_entrega":      [[400, 700], [600, 700], [600, 900], [400, 900]],
        }

    # ------------------------------------------------------------
    # PIXMAP
    # ------------------------------------------------------------
    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        super().setPixmap(pixmap)
        self.update()

    # ------------------------------------------------------------
    # CONVERSIÓN DE COORDENADAS
    # ------------------------------------------------------------
    def get_scaled_point(self, point_percentage: QPoint) -> QPoint:
        width = self.width()
        height = self.height()
        x = int(point_percentage.x() * width / 1000)
        y = int(point_percentage.y() * height / 1000)
        return QPoint(x, y)

    def get_percentage_point(self, point_pixel: QPoint) -> QPoint:
        width = self.width()
        height = self.height()
        if width == 0 or height == 0:
            return QPoint(0, 0)

        x = int(point_pixel.x() * 1000 / width)
        y = int(point_pixel.y() * 1000 / height)

        x = max(0, min(x, 1000))
        y = max(0, min(y, 1000))
        return QPoint(x, y)

    # ------------------------------------------------------------
    # DIBUJO
    # ------------------------------------------------------------
    def paintEvent(self, event):
        super().paintEvent(event)

        # Si points_hidden está activo, no dibujar ningún overlay
        if self.points_hidden:
            return

        # Si los puntos están ocultos y no hay door/entrega features activas, no dibujar nada
        if not self.show_points and not (self.door_active or self.door_direction_active or self.entrega_active):
            return

        if self.width() < 1 or self.height() < 1 or self.current_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        last_p_pixel = None
        if len(self.points) > 0:
            for i, p_percentage in enumerate(self.points):
                p_pixel = self.get_scaled_point(p_percentage)

                # Líneas
                if last_p_pixel is not None:
                    painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
                    painter.drawLine(last_p_pixel, p_pixel)
                last_p_pixel = p_pixel

                # Puntos
                color = Qt.red if i == self.active_point_index else Qt.yellow
                painter.setPen(QPen(Qt.black, 2))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(p_pixel, self.point_radius, self.point_radius)

            # Cerrar polígono
            if last_p_pixel is not None:
                first_p_pixel = self.get_scaled_point(self.points[0])
                painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
                painter.drawLine(last_p_pixel, first_p_pixel)

        # --- Dibujar door ROI si está activo ---
        if self.door_active and len(self.door_points) > 0:
            last_dp = None
            for i, dp in enumerate(self.door_points):
                dp_pixel = self.get_scaled_point(dp)
                if last_dp is not None:
                    painter.setPen(QPen(Qt.cyan, 1, Qt.SolidLine))
                    painter.drawLine(last_dp, dp_pixel)
                last_dp = dp_pixel

                color = Qt.green if (self.edit_target == 'door' and i == self.active_point_index) else Qt.blue
                painter.setPen(QPen(Qt.black, 2))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(dp_pixel, self.point_radius, self.point_radius)

            # cerrar polígono door
            if last_dp is not None and len(self.door_points) > 1:
                first_dp = self.get_scaled_point(self.door_points[0])
                painter.setPen(QPen(Qt.cyan, 1, Qt.SolidLine))
                painter.drawLine(last_dp, first_dp)

        # --- Dibujar Entrega ROI si está activo (verde) ---
        if self.entrega_active and len(self.entrega_points) > 0:
            last_ep = None
            for i, ep in enumerate(self.entrega_points):
                ep_pixel = self.get_scaled_point(ep)
                if last_ep is not None:
                    painter.setPen(QPen(Qt.green, 1, Qt.SolidLine))
                    painter.drawLine(last_ep, ep_pixel)
                last_ep = ep_pixel

                color = Qt.white if (self.edit_target == 'entrega' and i == self.active_point_index) else Qt.green
                painter.setPen(QPen(Qt.black, 2))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(ep_pixel, self.point_radius, self.point_radius)

            # cerrar polígono entrega
            if last_ep is not None and len(self.entrega_points) > 1:
                first_ep = self.get_scaled_point(self.entrega_points[0])
                painter.setPen(QPen(Qt.green, 1, Qt.SolidLine))
                painter.drawLine(last_ep, first_ep)

        # --- Dibujar dirección de puerta si está activa ---
        if self.door_direction_active and len(self.door_direction) >= 2:
            p0 = self.get_scaled_point(self.door_direction[0])
            p1 = self.get_scaled_point(self.door_direction[1])
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.drawLine(p0, p1)

            # puntos extremos
            for i, dpt in enumerate(self.door_direction):
                d_pixel = self.get_scaled_point(dpt)
                color = Qt.magenta if (self.edit_target == 'direction' and i == self.active_point_index) else Qt.white
                painter.setPen(QPen(Qt.black, 2))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(d_pixel, self.point_radius, self.point_radius)

        painter.end()


    # ------------------------------------------------------------
    # EVENTOS DEL MOUSE
    # ------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        # Si los puntos están visualmente ocultos, no permitir interacción
        if self.points_hidden:
            return super().mousePressEvent(event)
        # Permitir interacción si: puntos visibles, o door/entrega activo, o estamos editando
        if not self.show_points and not (self.door_active or self.door_direction_active or self.entrega_active or self.edit_target != 'roi'):
            return
        if event.button() == Qt.LeftButton:
            # intentar seleccionar en el orden: edit_target actual, luego el resto
            all_sets = [
                ('roi', self.points),
                ('door', self.door_points),
                ('entrega', self.entrega_points),
                ('direction', self.door_direction),
            ]
            # Priorizar el edit_target actual
            sets = [s for s in all_sets if s[0] == self.edit_target]
            sets += [s for s in all_sets if s[0] != self.edit_target]

            for name, pts in sets:
                if not pts:
                    continue
                for i, p_percentage in enumerate(pts):
                    p_pixel = self.get_scaled_point(p_percentage)
                    dx = event.pos().x() - p_pixel.x()
                    dy = event.pos().y() - p_pixel.y()
                    distance = (dx**2 + dy**2)**0.5
                    if distance < self.point_radius:
                        # si selecciona otro conjunto, cambiar edit_target
                        self.edit_target = name
                        self.active_point_index = i
                        self.update()
                        return
        super().mousePressEvent(event)



    def mouseMoveEvent(self, event: QMouseEvent):
        if self.points_hidden:
            return super().mouseMoveEvent(event)
        if not self.show_points and not (self.door_active or self.door_direction_active or self.entrega_active or self.edit_target != 'roi'):
            return
        if self.active_point_index != -1 and event.buttons() & Qt.LeftButton:
            new_pos_pixel = event.pos()
            new_pos_pixel.setX(max(0, min(new_pos_pixel.x(), self.width())))
            new_pos_pixel.setY(max(0, min(new_pos_pixel.y(), self.height())))
            new_pos_percentage = self.get_percentage_point(new_pos_pixel)

            if self.edit_target == 'roi':
                self.points[self.active_point_index] = new_pos_percentage
            elif self.edit_target == 'door':
                self.door_points[self.active_point_index] = new_pos_percentage
            elif self.edit_target == 'entrega':
                self.entrega_points[self.active_point_index] = new_pos_percentage
            else:
                # direction
                self.door_direction[self.active_point_index] = new_pos_percentage

            self.update()
        super().mouseMoveEvent(event)



    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.points_hidden:
            return super().mouseReleaseEvent(event)
        if not self.show_points and not (self.door_active or self.door_direction_active or self.entrega_active or self.edit_target != 'roi'):
            return
        if event.button() == Qt.LeftButton and self.active_point_index != -1:
            self.active_point_index = -1
            self.update()
            self.point_change.emit(
                        self.qpoints_to_list(qpoints = self.points),
                        self.show_points,
                        self.qpoints_to_list(qpoints = self.door_points),
                        self.door_active,
                        self.qpoints_to_list(qpoints = self.door_direction),
                        self.door_direction_active,
                        self.qpoints_to_list(qpoints = self.entrega_points),
                        self.entrega_active,
                    )
        super().mouseReleaseEvent(event)



    # ------------------------------------------------------------
    # OBTENER COORDENADAS EN PIXELES ORIGINALES
    # ------------------------------------------------------------
    def get_coordinates(self, image_width: int, image_height: int) -> list[list[int]]:
        if image_width <= 0 or image_height <= 0:
            return []

        coordinates = []
        for p_percentage in self.points:
            x = int(p_percentage.x() * image_width / 1000)
            y = int(p_percentage.y() * image_height / 1000)
            coordinates.append([x, y])
        return coordinates


    def get_door_coordinates(self, image_width: int, image_height: int) -> list[list[int]]:
        if image_width <= 0 or image_height <= 0:
            return []
        coordinates = []
        for p_percentage in self.door_points:
            x = int(p_percentage.x() * image_width / 1000)
            y = int(p_percentage.y() * image_height / 1000)
            coordinates.append([x, y])
        return coordinates



    def get_door_direction_coordinates(self, image_width: int, image_height: int) -> list[list[int]]:
        if image_width <= 0 or image_height <= 0:
            return []

        coordinates = []
        for p_percentage in self.door_direction:
            x = int(p_percentage.x() * image_width / 1000)
            y = int(p_percentage.y() * image_height / 1000)
            coordinates.append([x, y])

        return coordinates


    def qpoints_to_list(self, qpoints: list[QPoint]) -> list[list[int]]:
        """Convierte una lista de QPoints a una lista de listas [[x, y], ...]"""
        return [[p.x(), p.y()] for p in qpoints]



    def list_to_qpoints(self, data: list[list[int]]) -> list[QPoint]:
        """Convierte una lista de listas [[x, y], ...] a una lista de QPoints"""
        # Usamos una lista de comprensión para instanciar los QPoints
        return [QPoint(coord[0], coord[1]) for coord in data]

    # ------------------------------------------------------------
    # Métodos para door ROI / direction
    # ------------------------------------------------------------
    def set_door_roi(self, data: list[list[int]]):
        self.door_points = self.list_to_qpoints(data)
        self.update()



    def set_door_direction(self, data: list[list[int]]):
        # espera exactamente 2 puntos
        if data is None:
            self.door_direction = []
        else:
            self.door_direction = self.list_to_qpoints(data)
        self.update()



    def toggle_door_roi(self, state: bool = None):
        if state is None:
            self.door_active = not self.door_active
        else:
            self.door_active = bool(state)
        self.update()



    def toggle_door_direction(self, state: bool = None):
        if state is None:
            self.door_direction_active = not self.door_direction_active
        else:
            self.door_direction_active = bool(state)
        self.update()



    # ------------------------------------------------------------
    # Métodos para Entrega ROI
    # ------------------------------------------------------------
    def get_entrega_coordinates(self, image_width: int, image_height: int) -> list[list[int]]:
        if image_width <= 0 or image_height <= 0:
            return []
        coordinates = []
        for p_percentage in self.entrega_points:
            x = int(p_percentage.x() * image_width / 1000)
            y = int(p_percentage.y() * image_height / 1000)
            coordinates.append([x, y])
        return coordinates

    def set_entrega_roi(self, data: list[list[int]]):
        self.entrega_points = self.list_to_qpoints(data)
        self.update()

    def toggle_entrega_roi(self, state: bool = None):
        if state is None:
            self.entrega_active = not self.entrega_active
        else:
            self.entrega_active = bool(state)
        self.update()

    def set_edit_target(self, target: str):
        if target in ('roi', 'door', 'direction', 'entrega'):
            self.edit_target = target
            self.active_point_index = -1
            self.update()