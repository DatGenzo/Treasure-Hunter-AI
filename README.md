# BÁO CÁO MÔN HỌC: TRÍ TUỆ NHÂN TẠO
*TRƯỜNG ĐẠI HỌC CÔNG NGHỆ KỸ THUẬT TP. HỒ CHÍ MINH (HCMUTE)*
*KHOA CÔNG NGHỆ THÔNG TIN*

## ĐỀ TÀI: TREASURE HUNTER AI

- **Lớp học phần:** 252ARIN330585_08
- **Giảng viên hướng dẫn:** TS. Phan Thị Huyền Trang
- **Thời gian hoàn thành:** Tháng 6 năm 2026

## Nhóm sinh viên thực hiện:
1. **Trần Quyết Chiến** - 24110171
2. **Đỗ Thành Đạt** - 24110192
3. **Lâm Huy Bách** - 24110165

---

## 1. Giới thiệu dự án
**Treasure Hunter AI** xây dựng một trò chơi phiêu lưu 2D hoàn chỉnh trên nền tảng `pygame-ce`. Dự án chuyển hóa bối cảnh nhà khảo cổ khám phá ngôi đền cổ đại thành một nền tảng tích hợp và trực quan hóa **19 thuật toán AI** thuộc 6 nhóm khác nhau xuyên suốt **7 Level**.

Bài toán cốt lõi yêu cầu nhân vật (Player) phải tự động tìm đường, né tránh chướng ngại vật địa hình, thu thập vật phẩm chiến lược, giải câu đố mã hóa, chiến đấu với quái vật và tìm lối thoát (Exit) trên bản đồ lưới 2D.

### Quy ước hệ thống ô lưới (TileMap):
* **FLOOR** ($cost = 1$): Không gian trống.
* **WALL**: Vật cản cứng không thể đi qua.
* **MUD** ($cost = 3$): Vùng bùn lầy di chuyển chậm.
* **WATER** ($cost = 5$): Vùng nước chi phí cao.
* **TRAP** ($cost = 2 + \text{damage}$): Bẫy gây sát thương ($10\text{ HP}$).
* **LAVA** ($cost = 8 + \text{damage}$): Dung nham cực kỳ nguy hiểm.

### Cơ chế hiển thị 2 Giai Đoạn (Phases):
* **Phase 1 (Tìm kiếm trạng thái):** Thuật toán AI chạy ngầm tính toán và trả về tập hợp các `StepResult` (bao gồm *frontier, explored, current_path*). Quá trình "suy nghĩ" này được tái hiện trực quan thông qua hệ thống **Visualisation Overlay**.
* **Phase 2 (Thực thi - GoalPlanner):** Nhân vật tự động di chuyển thực hiện chuỗi nhiệm vụ liên kết (Sub-goals): `Thu thập Key` $\rightarrow$ `Mở Door` $\rightarrow$ `Giải Puzzle` $\rightarrow$ `Chiến đấu Monster` $\rightarrow$ `Thoát Exit`.

---

## 2. Mô hình PEAS
* **P - Performance Measure:** Tìm đường hợp lệ đến Exit, tối thiểu hóa số node duyệt (`nodes_expanded`), tối thiểu hóa chi phí (`path_cost`), né bẫy bảo toàn máu (HP) và thu thập kho báu. Hệ thống **Star Rating (1-3★)** đánh giá tổng hợp hiệu năng dựa trên độ tối ưu so với đường đi chuẩn.
* **E - Environment:** Bản đồ lưới kích thước $30 \times 22$ (Level 1-6) hoặc $40 \times 30$ (Level 7). Môi trường thay đổi linh hoạt: tĩnh đầy đủ thông tin, bị sương mù che phủ (Fog of War), chứa ma trận ràng buộc logic hoặc đối kháng thời gian thực.
* **A - Actuators:** Di chuyển 4 hướng (`move_n`, `move_s`, `move_e`, `move_w`), tương tác nhặt vật phẩm (Key, Treasure, Potion), mở Door, kích hoạt puzzle trigger và các hành động combat (`ATTACK`, `DODGE`, `MOVE_L`, `MOVE_R`, `USE_POTION`).
* **S - Sensors:** Cảm biến vị trí Player $(\text{col}, \text{row})$, HP hiện tại, túi đồ (Inventory), các ô đã khám phá (`revealed tiles`), vị trí quái vật/vật phẩm, chi phí $g(n)$ và heuristic $h(n)$ (khoảng cách Manhattan). Trong Fog of War, tầm nhìn bị giới hạn trong bán kính 4 ô.

---

## 3. Hệ thống 19 Thuật toán AI theo 7 Level

### Nhóm 1: Uninformed Search (Level 1: The Dark Corridor)
*Môi trường mê cung tĩnh chỉ gồm FLOOR và WALL, chi phí đồng nhất.*
* **BFS (Breadth-First Search):** Sử dụng hàng đợi FIFO queue. Quét đều theo lớp như các vòng sóng đồng tâm rộng $360^{\circ}$, luôn đảm bảo tìm thấy đường ngắn nhất theo số bước.
* **DFS (Depth-First Search):** Sử dụng Stack. Đi sâu tối đa vào một nhánh cho đến ngõ cụt trước khi thực hiện quay lui (Backtrack), hiển thị trực quan dưới dạng một dải overlay dài.
* **IDDFS (Iterative Deepening DFS):** Lặp tăng dần giới hạn độ sâu (Depth limit) nhằm kết hợp ưu điểm bộ nhớ thấp của DFS và tính tối ưu của BFS.

### Nhóm 2: Informed Search (Level 2: Weighted Ruins)
*Bản đồ địa hình phức tạp có trọng số, áp dụng khoảng cách Heuristic Manhattan để định hướng tìm kiếm.*
* **UCS (Uniform Cost Search):** Mở rộng frontier theo đường đồng mức chi phí (`cost contour`), chấp nhận đi đường vòng xa để né tránh các vùng chi phí cao như MUD hay WATER.
* **Greedy Best-First Search:** Di chuyển bất chấp dựa hoàn toàn vào giá trị heuristic tốt nhất đến đích, dễ đâm đầu vào bẫy chi phí cao hoặc ngõ cụt hình chữ U.
* **A\* Search:** Thuật toán tối ưu nhất nhờ cân bằng hàm đánh giá $f(n) = g(n) + h(n)$, giúp frontier hướng thẳng về đích nhưng vẫn khôn ngoan lách qua các vùng địa hình xấu.

### Nhóm 3: Local Search (Level 3: The Shifting Heights)
*Bản đồ dạng nếp gấp địa hình tạo ra nhiều ngõ cụt sát mục tiêu (Local Optima).*
* **Hill Climbing:** Di chuyển thuần túy theo hướng dốc heuristic tốt nhất, dễ dàng hiển thị trạng thái bị kẹt `"Stuck!"` tại các thung lũng góc khuất trước tường chắn.
* **Simulated Annealing:** Chấp nhận các bước đi xấu dựa trên xác suất giảm dần theo nhiệt độ (Temperature) khởi đầu từ $100.0$, giúp nhân vật có cơ hội thoát khỏi các bẫy local optima.
* **Local Beam Search ($k=4$):** Duy trì song song 4 trạng thái ứng viên để bổ trợ thông tin tọa độ tốt nhất cho nhau, tăng tỉ lệ bủa vây đích thành công.

### Nhóm 4: Complex Environment (Level 4: Temple of Shadows)
*Bản đồ bị che khuất hoàn toàn bởi sương mù (Fog of War, sensor radius = 4), AI phải xử lý bất định và thiếu quan sát.*
* **AND-OR Search:** Lập kế hoạch dự phòng dạng cây đối phó với điều kiện môi trường thay đổi ngẫu nhiên hoặc các trạng thái không tất định.
* **No Observation (Sensorless):** Lập kế hoạch khi hoàn toàn mù thông tin cảm biến, tính toán dựa trên tập hợp tất cả các trạng thái khả dĩ (Belief Set toàn bản đồ).
* **Partially Observable:** Tính toán và cập nhật lộ trình di chuyển dựa trên Belief State thu hẹp dần mỗi khi sensor quét và phát hiện thêm các ô trống mới.
* **Online Search (LRTA\*):** Khám phá thời gian thực, liên tục cập nhật và sửa đổi trực tiếp giá trị Heuristic ngay trên overlay của bản đồ trong quá trình di chuyển tương tác.

### Nhóm 5: Constraint Satisfaction - CSP (Level 5: The Puzzle Sanctum)
*Giải câu đố ma trận cổ đại Latin Square $3 \times 3$ (mỗi ô là biến, miền giá trị gồm tập màu ngọc {RED, GREEN, BLUE}, ràng buộc khác màu trên hàng/cột).*
* **Backtracking CSP:** Gán thử màu tuần tự có hệ thống, tự động quay lui khi phát hiện vi phạm ràng buộc trên hàng hoặc cột.
* **Constraint Propagation (AC-3):** Kiểm tra tính nhất quán cung (Arc Consistency) để sàng lọc và cắt tỉa miền giá trị khả dụng của các biến sớm, giảm nhánh sai.
* **Min-Conflicts:** Khởi tạo ma trận ngẫu nhiên, liên tục chọn ô bị lỗi và sửa đổi bằng màu ít gây xung đột nhất. Giải quyết câu đố cực nhanh chỉ sau vài bước lặp.

### Nhóm 6: Adversarial Search (Level 6: Monster Lair)
*Hệ thống chuyển sang đấu trường Combat 1D thời gian thực chống lại quái vật di chuyển có trí tuệ (Trò chơi đối kháng Zero-Sum).*
* **Minimax:** Giả định quái vật luôn chọn nước đi tối ưu nhất để hại mình (MIN) để đưa ra hành động phản công hoặc phòng thủ tối ưu nhất cho mình (MAX) với `depth = 4`.
* **Alpha-Beta Pruning:** Cắt tỉa các nhánh tính toán dư thừa (các nhánh bị tỉa hiển thị gạch ngang đỏ trên bảng điều khiển), nâng giới hạn tính toán lên `depth = 6` giữ nguyên độ mượt.
* **Expectimax:** Thay thế nút MIN bằng nút tính giá trị trung bình (Xác suất quái vật di chuyển lỗi hoặc ngẫu nhiên chiếm 30%), giúp Player táo bạo chớp thời cơ dứt điểm.

### Level 7: Grand Temple (Tổng hợp)
* Bản đồ tối cao thử thách đồng thời phối hợp cả 19 thuật toán AI hoạt động nhịp nhàng để giải quyết toàn bộ chuỗi nhiệm vụ phức tạp của ngôi đền cổ.

---

## 4. Hướng dẫn Cài đặt & Khởi chạy

### Yêu cầu hệ thống:
* Python 3.10 trở lên
* Thư viện đồ họa nâng cao `pygame-ce`

### Các bước cài đặt:
```bash
# Tạo và kích hoạt môi trường ảo (Khuyến nghị)
python -m venv .venv

# Kích hoạt trên Windows:
.venv\Scripts\activate
# Kích hoạt trên macOS/Linux:
source .venv/bin/activate

# Cài đặt các thư viện bắt buộc
pip install pygame-ce pytest

### Khởi chạy trò chơi:
```bash
python main.py
```

### Chạy Unit Test (Kiểm tra AI):
```bash
python -m pytest tests/ -v
```

### Hướng dẫn sử dụng UI:
AI Panel: Lựa chọn Nhóm thuật toán và Thuật toán cụ thể qua thanh dropdown bên bảng HUD phải. Tùy chỉnh tốc độ qua slider AI Search Speed.

Nút RUN: Bắt đầu kích hoạt Phase 1 chạy thuật toán tìm đường ngầm.

Thanh Replay (Time-lapse):

< / >: Lùi lại hoặc tiến tới đúng 1 bước duyệt (node expansion) trên bản đồ.

AUTO / STOP: Tự động phát hoặc tạm dừng hoạt ảnh mô phỏng quá trình duyệt node.

>>: Bỏ qua hoạt ảnh, kết xuất hiển thị ngay lộ trình đích cuối cùng.

Nút FIRE (hoặc COLLECT): Kích hoạt Phase 2, đưa nhân vật vào trạng thái tự động di chuyển thực thi nhiệm vụ theo chuỗi kết quả đã lập kế hoạch.

Phím tắt nhanh: Phím mũi tên Trái/Phải để lùi/tiến bước duyệt, phím Esc để thoát nhanh chương trình.
