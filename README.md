# ThemDauTiengViet

Xử lý ngôn ngữ tự nhiên cho tiếng Việt là một bài toán được nhiều tổ chức nghiên cứu trong nhiều năm. Một trong các nhiệm vụ quan trọng trong các bài toán xử lý ngôn ngữ tiếng Việt là chuẩn hóa, trong đó Thêm dấu tiếng Việt là một trong các bài toán phổ biến nhất.

Trong cuộc thi này, các đội chơi được giao nhiệm vụ thêm dấu cho các câu và đoạn văn không dấu.

Cấu trúc của bộ dữ liệu như sau:

``` 
vietnamese_tone_prediction
    .
    ├── sample_submission.csv
    ├── test.txt
    ├── test_word_per_line.txt
    └── train.txt
```

Dữ liệu huấn luyện
Dữ liệu huấn luyện (file train.txt) gồm 2,126,280 dòng. Mỗi dòng là một câu hoặc một đoạn văn. Dữ liệu này được crawl từ nhiều nguồn và chưa được xử lý, có thể lẫn các từ không phải tiếng Việt nhưng tỉ lệ nhỏ.

Dữ liệu kiểm tra
Dữ liệu kiểm tra (file test.txt) bao gồm 8240 dòng, mỗi dòng là một câu hoặc một đoạn văn đã được bỏ dấu. Ba ký tự đầu tiên trước dấu phẩy (,) của mỗi dòng là mã dòng. Tương tự như các cuộc thi trước, dữ liệu kiểm tra công khai và bí mật đã được trộn lẫn vào nhau một cách ngẫu nhiên. Dữ liệu công khai để hiển thị điểm trong quá trình cuộc thi diễn ra. Dữ liệu bí mật để tính kết quả cuối cùng.

Cách mã hóa tiếng Việt có dấu
Để đồng nhất việc đánh giá kết quả, các từ tiếng Việt được mã hóa dưới dạng VNI chuẩn hóa. Cụ thể:

``` 
â = a6, Â = A6
ă = a8, Ă = A8
đ = d9, Đ = D9
ê = e6, Ê = E6
ô = o6, Ô = O6
ơ = o7, Ơ = O7
ư = u7, Ư = U7
sắc = 1
huyền = 2
hỏi = 3
ngã = 4
nặng = 5
``` 

Phần dấu được đẩy về cuối của mỗi chữ. Một vài ví dụ:

``` 
Con = Con
Đường = D9u7o7ng2
Trí = Tri1
Tuệ = Tue65
Nhân = Nha6n
Tạo = Tao5
``` 
Trong file nộp bài, nhãn của mỗi chữ là dãy chữ số viết theo thứ tự chuẩn hóa VNI.

``` 
|----------------+---------------+-------------------+--------------+
| **không dấu**  |  **Dự đoán**  | **VNI chuẩn hóa** | **Nộp bài**  |
+----------------+---------------+-------------------+--------------+
| Con            | Con           | Con               | 0            |
| Duong          | Đường         | D9u7o7ng2         | 9772         |
| Tri            | Trí           | Tri1              | 1            |
| Tue            | Tuệ           | Tue65             | 65           |
| nhan           | nhân          | nha6n             | 6            |
| tao            | tạo           | tao5              | 5            |
+----------------+---------------+-------------------+--------------+
``` 
