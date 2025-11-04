\encoding UTF8

--Создание таблиц
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(50) NOT NULL,
	surname VARCHAR(50) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOL DEFAULT FALSE,
    is_verify BOOL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE verify_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
	education_content TEXT NOT NULL,
	course_id INTEGER NOT NULL,
	duration_minutes INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

	FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE usersprogress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
	is_completed BOOL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
	FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

CREATE TABLE personal_access_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

--Создание курсов
INSERT INTO courses (title, description, price) VALUES
('Python для начинающих', 'Полный курс по основам Python программирования: переменные, условия и циклы, объектно-
ориентированное программирование', 7000),
('Веб-разработка для начинающих', 'Курс по основам веб-разработки: HTML, CSS, SCSS, JS', 5000),
('Базы данных и SQL', 'Основы работы с реляционными базами данных. На курсе будет использоваться PostgreSQL', 6000);

--Создание уроков
INSERT INTO lessons (title, description, education_content, duration_minutes, course_id) VALUES
('Введение в Python', 
'На уроке вы узнаете интересные факты о языке программирования Python и напишите свою первую программу', 
'Python — это современный язык программирования, который ценят за его простой и лаконичный синтаксис, похожий на обычный английский. Он чрезвычайно популярен в таких областях, как веб-разработка, анализ данных и искусственный интеллект. Сегодня вы напишете свою первую программу, используя функцию print(), которая выводит текст на экран. Для этого просто введите команду print("Привет, мир!") в своём редакторе кода. Запустите программу, нажав на соответствующую кнопку в вашей среде разработки, и вы сразу увидите результат своей работы в окне терминала. Поздравляем, вы только что сделали первый шаг в мир программирования!', 
60, 
1),

('Переменные и типы данных', 
'На уроке вы узнаете, что такое переменные и какие типы данных существуют в Python', 
'Переменные в Python — это контейнеры для хранения данных, которые создаются простым присваиванием значения. Основные типы данных включают целые числа (int), дробные числа (float), строки (str) и логические значения (bool). Вы научитесь создавать переменные и работать с разными типами данных, а также освоите базовые операции между ними. Практическое задание поможет закрепить эти concepts на примерах. Понимание переменных и типов данных — фундамент для дальнейшего изучения программирования.', 
90, 
1),

('Введение в веб-разработку', 
'На уроке вы узнаете, из чего состоит любая веб-страница, познакомитесь с её структурой', 
'Веб-разработка — это процесс создания веб-сайтов и приложений, который включает фронтенд (визуальная часть) и бэкенд (серверная логика). Любая веб-страница состоит из HTML-структуры, CSS-стилей и JavaScript-логики. Вы узнаете, как эти технологии взаимодействуют между собой в браузере пользователя. На практике мы разберем структуру типичной веб-страницы и поймем, как происходит отображение контента. Этот урок даст вам полное представление о том, как создаются современные веб-сайты.', 
80, 
2),

('Язык разметки HTML', 
'На уроке вы познакомитесь с языком разметки HTML, который позволяет описать структуру любой веб-страницы', 
'HTML (HyperText Markup Language) — это стандартный язык разметки для создания веб-страниц, состоящий из тегов. Вы научитесь использовать основные теги: <html>, <head>, <body>, <h1>-<h6> для заголовков, <p> для параграфов и <div> для блоков. На практике создадите свою первую HTML-страницу с текстовым содержимым и узнаете о важности семантической разметки. Понимание HTML — это первый и самый важный шаг в становлении веб-разработчика.', 
120, 
2),

('Что такое база данных?', 
'На уроке вы узнаете о принципах работы реляционных баз данных', 
'База данных — это организованная коллекция данных, хранящаяся и обрабатываемая электронным способом. Реляционные базы данных организованы в виде таблиц, связанных между собой отношениями. Вы узнаете об основных понятиях: таблицы, строки, столбцы, первичные и внешние ключи. Мы разберем преимущества реляционного подхода и основные операции с данными. Этот урок даст вам фундаментальное понимание того, как организовано хранение информации в современных приложениях.', 
40, 
3),

('Реляционная БД PostgreSQL', 
'На уроке вы познакомитесь с реляционной БД PostgreSQL и удобным интерфейсом pgAdmin для работы с ней', 
'PostgreSQL — это мощная объектно-реляционная система управления базами данных с открытым исходным кодом. Вы научитесь устанавливать соединение с базой данных и освоите базовые операции через интерфейс pgAdmin. На практике создадите свою первую базу данных, таблицу и выполните простые SQL-запросы на выборку данных. Работа с PostgreSQL и pgAdmin — ключевой навык для backend-разработчика и аналитика данных. Этот инструмент широко используется в промышленной разработке благодаря своей надежности и функциональности.', 
80, 
3);

--Создание пользователей
INSERT INTO users (firstname, surname, email, password_hash, is_admin, is_verify) VALUES
('admin', 'admin', 'admin@example.com', '$2b$12$1ZCmVbl.EDo1Lxzy1r5ymu1lPfKBz4BxRezPwYL./31dXGPy5G8NW', TRUE, TRUE),
('user', 'user', 'user@example.com', '$2b$12$u5isUS5BT8p5PnWK1G0fHOWSUf/jNgdO3b7B6ckjiReH4oK8RDmHW', FALSE, TRUE);

--Зачисление user на курсы
INSERT INTO usersprogress (user_id, course_id, lesson_id) VALUES
(2, 1, 1),
(2, 1, 2),
(2, 3, 5),
(2, 3, 6);