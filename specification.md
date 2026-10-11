# 📋 Cafe Personnel Management System - Technical Specification

## ۱. معرفی و هدف پروژه (Overview)
یک نرم‌افزار دسکتاپ سبک با زبان پایتون جهت مدیریت پرسنل، کنترل تردد، ثبت مرخصی، شیفت‌بندی ثابت و محاسبه کارکرد پرسنل کافه. این سیستم بدون نیاز به فریم‌ورک‌های وب (مانند جنگو) طراحی شده و بر پایه رابط کاربری دسکتاپ محلی (Desktop GUI) و دیتابیس لوکال اجرا می‌شود.

---

## ۲. معماری و استک فنی (Tech Stack)
* **زبان:** Python 3.10+
* **رابط کاربری (GUI):** `CustomTkinter` یا `PyQt6 / PySide6` (پیشنهاد پیش‌فرض: CustomTkinter برای سبکی و ظاهر مدرن)
* **پایگاه داده:** `SQLite3` (لوکال، سبک و بدون نیاز به نصب سرور دیتابیس)
* **مدیریت تاریخ و زمان:** `jdatetime` (پشتیبانی کامل از تاریخ شمسی و زمان ایران)
* **مدیریت گزارشات:** `Pandas` / `OpenPyXL` (برای خروجی اکسل در صورت نیاز)

---

## ۳. نقش‌ها و سطوح دسترسی (Roles & Access Control)

### ۱. بخش پرسنل (Staff Kiosk)
* **بدون نیاز به پسورد/احراز هویت پیچیده:** برای سرعت عمل بالا در محیط شلوغ کافه.
* پرسنل تنها با انتخاب نام خود (یا کد پرسنلی ساده) می‌توانند عملیات زیر را انجام دهند:
  1. ثبت ورود (Check-in)
  2. ثبت خروج (Check-out)
  3. مشاهده وضعیت آخرین تردد امروز
  4. ارسال درخواست مرخصی (ساعتی یا روزانه با ذکر علت)
* عدم دسترسی مطلق به گزارش‌ها، حقوق، تنظیمات شیفت و پنل مدیریت.

### ۲. بخش مدیریت (Admin Panel)
* **حفاظت‌شده با رمز عبور (Admin Auth):** ورود فقط با پسورد مدیر.
* امکانات کامل مدیریت:
  1. تعریف، ویرایش و غیرفعال‌سازی پرسنل.
  2. تعریف شیفت کاری ثابت روزانه برای هر پرسنل (مثلاً شنبه تا جمعه ۸:۰۰ تا ۱۲:۰۰).
  3. کارتابل تایید یا رد درخواست‌های مرخصی.
  4. اصلاح ترددهای ناقص (ثبت دستی ورود/خروج در صورت فراموشی پرسنل).
  5. ثبت پاداش و کسورات مالی برای هر پرسنل.
  6. مشاهده گزارشات تخلفات (تاخیر، تعجیل، غیبت) و کارکرد کل ماه.

---

## ۴. طراحی پایگاه داده (Database Schema)

### جدول ۱: پرسنل (`employees`)
* `id` (INTEGER, Primary Key, Auto Increment)
* `full_name` (TEXT, Not Null)
* `personnel_code` (TEXT, Unique, Not Null)
* `phone` (TEXT)
* `hourly_rate` (REAL - دستمزد ساعتی / پایه)
* `is_active` (BOOLEAN, Default True)
* `created_at` (TEXT - تاریخ شمسی)

### جدول ۲: شیفت کاری پرسنل (`shifts`)
* `id` (INTEGER, Primary Key)
* `employee_id` (INTEGER, Foreign Key -> employees.id)
* `start_time` (TEXT, Not Null) -- فرمت HH:MM (مثلاً 08:00)
* `end_time` (TEXT, Not Null)   -- فرمت HH:MM (مثلاً 12:00)
* `tolerance_minutes` (INTEGER, Default 5) -- مهلت مجاز تاخیر بدون جریمه

### جدول ۳: تردد و حضور و غیاب (`attendances`)
* `id` (INTEGER, Primary Key)
* `employee_id` (INTEGER, Foreign Key -> employees.id)
* `jalali_date` (TEXT, Not Null) -- فرمت YYYY/MM/DD
* `check_in` (TEXT)              -- فرمت HH:MM:SS
* `check_out` (TEXT)             -- فرمت HH:MM:SS
* `is_manual_entry` (BOOLEAN, Default False) -- آیا توسط مدیر اصلاح شده؟
* `status` (TEXT)                -- 'open', 'completed', 'missed_checkout'
* `delay_minutes` (INTEGER, Default 0)  -- تاخیر در ورود
* `early_leave_minutes` (INTEGER, Default 0) -- تعجیل در خروج
* `overtime_minutes` (INTEGER, Default 0) -- اضافه کاری

### جدول ۴: مرخصی‌ها (`leave_requests`)
* `id` (INTEGER, Primary Key)
* `employee_id` (INTEGER, Foreign Key -> employees.id)
* `leave_type` (TEXT)            -- 'daily' یا 'hourly'
* `start_date` (TEXT, Not Null)  -- YYYY/MM/DD
* `end_date` (TEXT)              -- YYYY/MM/DD (برای مرخصی روزانه)
* `start_time` (TEXT)            -- HH:MM (برای مرخصی ساعتی)
* `end_time` (TEXT)              -- HH:MM (برای مرخصی ساعتی)
* `reason` (TEXT)
* `status` (TEXT, Default 'pending') -- 'pending', 'approved', 'rejected'
* `created_at` (TEXT)

### جدول ۵: پاداش و کسورات (`adjustments`)
* `id` (INTEGER, Primary Key)
* `employee_id` (INTEGER, Foreign Key -> employees.id)
* `jalali_date` (TEXT, Not Null)
* `type` (TEXT, Not Null)        -- 'bonus' (پاداش) یا 'deduction' (کسورات)
* `amount` (REAL, Not Null)      -- مبلغ به تومان
* `reason` (TEXT, Not Null)

### جدول ۶: تنظیمات سیستم (`settings`)
* `key` (TEXT, Primary Key)
* `value` (TEXT)

---

## ۵. منطق‌های محاسباتی و بیزینس نرم‌افزار (Business Logic)

### ۱. ثبت تردد هوشمند
* اگر پرسنل در روز جاری خروجی ثبت نکرده و برای بار اول دکمه را بزند -> **ورود** ثبت می‌شود.
* اگر دکمه را مجدداً بزند -> به عنوان **خروج** ثبت می‌شود.
* محاسبه خودکار تاخیر: مقایسه زمان ورود با `shifts.start_time`.
* محاسبه تعجیل یا اضافه‌کاری بر اساس `shifts.end_time`.

### ۲. حل معضل فراموشی خروج (Missed Punch)
* اگر پرسنلی ورود زده باشد اما تا پایان روز خروج نزند، وضعیت رکورد به `missed_checkout` تغییر می‌کند.
* در پنل مدیریت، یک بخش اختصاصی برای «ترددهای بلاتکلیف» وجود دارد که مدیر می‌تواند ساعت خروج واقعی را ثبت کند تا محاسبه ساعت کاری تکمیل شود.

### ۳. فرآیند تایید مرخصی (Workflow)
1. پرسنل از پنل کاربری فرم مرخصی (ساعتی یا روزانه) را پر می‌کند.
2. وضعیت در دیتابیس به صورت `pending` ذخیره می‌شود.
3. در پنل مدیر یک بخش با نشانگر نوتیفیکیشن درخواست‌های جدید ظاهر می‌شود.
4. مدیر با زدن دکمه «تایید» یا «رد»، وضعیت را به‌روزرسانی می‌کند.
5. روزهایی که مرخصی تاییدشده روزانه دارند به عنوان غیبت غیرمجاز شمرده نمی‌شوند.

### ۴. تاریخ و تقویم شمسی
* تمامی نمایش‌ها و فیلترها (امروز، این هفته، این ماه) بر اساس تقویم جلالی (`jdatetime`) انجام می‌شود.


