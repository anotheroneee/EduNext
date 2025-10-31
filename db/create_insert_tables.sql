\encoding UTF8

--Создание таблиц
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(50) NOT NULL,
	surname VARCHAR(50) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) UNIQUE NOT NULL,
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
	time_spent_minutes INTEGER DEFAULT 0,
	is_completed BOOL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
	FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

--Наполнение таблиц с курсами и уроками
INSERT INTO courses (title, description, price) VALUES
('Python для начинающих', 'Полный курс по основам Python программирования: переменные, условия и циклы, объектно-
ориентированное программирование', 7000),
('Веб-разработка для начинающих', 'Курс по основам веб-разработки: HTML, CSS, SCSS, JS', 5000),
('Базы данных и SQL', 'Основы работы с реляционными базами данных. На курсе будет использоваться PostgreSQL', 6000);

INSERT INTO lessons (title, description, education_content, duration_minutes, course_id) VALUES
('Введение в Python', 'На уроке вы узнаете интересные факты о языке программирования Python и напишите 
свою первую программу', '*ссылка на видео* *ссылка на презентацию*', 60, 1),
('Переменные и типы данных', 'На уроке вы узнаете, что такое переменные
и какие типы данных существуют в Python', '*ссылка на видео* *ссылка на презентацию*', 90, 1),

('Введение в веб-разработку', 'На уроке вы узнаете, из чего состоит любая веб-страница, познакомитесь с 
её структурой', '*ссылка на видео* *ссылка на презентацию*', 80, 2),
('Язык разметки HTML', 'На уроке вы познакомитесь с языком разметки HTML, который позволяет 
описать структуру любой веб-страницы', '*ссылка на видео* *ссылка на презентацию*', 120, 2),

('Что такое база данных?', 'На уроке вы узнаете о принципах работы реляционных баз данных', 
'*ссылка на видео* *ссылка на презентацию*', 40, 3),
('Реляционная БД PostgreSQL', 'На уроке вы познакомитесь с реляционной БД PostgreSQL и удобным интерфейсом
pgAdmin для работы с ней', '*ссылка на видео* *ссылка на презентацию*', 80, 3);