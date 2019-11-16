from sys import argv, exit
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTableWidgetItem, QInputDialog
import sqlite3
import requests, bs4
import datetime
import calendar


""" Проект Яндекс Лицея, Гуков Артём. Исходный python file. 
Здесь реализованы классы Cinema, Times, Films, Cinemas, All. Они отвечают за работы PyQt интерфейса.
Также в них идёт получение информации о сеансах, фильмах, кинотеатрах базы данных afisha.
Класс Cinema - главное окно PyQt. Класс Times отвечает за случай, когда пользователь ввёл и кинотеатр, и фильм.
Тогда программа выведет все сеансы в данном кинотеатре с данным фильмом. Также его формат и продолжительность.
Класс Film - случай, когда введён только кинотеатр. 
Тогда всё будет также, как и с классом Times, только для каждого фильма в кинотеатре.
Класс Cinemas - случай, когда введён только фильм. Тогда программа выдаст все кинотеатры, где он идёт, со
временем и форматом.
Последний класс All - случай, когда не ввели ничего. Тогда программа просто выдас все сеансы.
Замечу, что всё выдаётся на выбранную дату.
Перед запуском PyQt, программа парсит сайт с сеансами города Калуга для получения информации о всех фильмах.
Это происходит в функциях fill и get_inf.
В среднем это занимает около 7 секунд
(получение информации, её обработка, очищение таблиц базы данных и их заполнение).
Програма записывает сеансы на ближайшие 8 дней(включая сегодняшний и следующие 7).
Если пользователь выбрал дату, на которую нет сеансов, програма это сообщит.
Удачного пользования!
"""


MONTHS = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6, 'июл': 7, 'авг': 8, 'сен': 9,
          'окт': 10, 'ноя': 11, 'дек': 12}


DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']


class Cinema(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi('ui_main.ui', self)
        self.times, self.cinemas, self.films, self.all = None, None, None, None
        self.pixmap = QPixmap('orig.jpg')
        self.image.setPixmap(self.pixmap)

        self.search.clicked.connect(self.run)
        self.choose.clicked.connect(self.choice)

    def run(self):

        date = self.calendar.selectedDate().toString().split()
        cinema = self.cinema.text()
        film = self.film.text()
        date = [date[3], str(MONTHS[date[1]]), date[2]]

        if cinema != 'Все' and film != 'Все':
            self.times = Times(self, film, cinema, date)
            self.times.show()
        elif cinema != 'Все':
            self.films = Films(self, cinema, date)
            self.films.show()
        elif film != 'Все':
            self.cinemas = Cinemas(self, film, date)
            self.cinemas.show()
        else:
            self.all = All(self, date)
            self.all.show()

    def choice(self):

        con = sqlite3.connect('afisha.db')
        cur = con.cursor()
        sql1 = """SELECT title FROM CInemas"""
        sql2 = """SELECT title FROM Films"""
        result1 = [i[0] for i in cur.execute(sql1).fetchall()]
        result2 = [i[0] for i in cur.execute(sql2).fetchall()]

        i, okBtnPressed = QInputDialog.getItem(self, "Кинотеатр",
                                               "Выберите кинотеатр",
                                               ('', *result1),
                                               0, False)
        if okBtnPressed:
            self.cinema.setText(i)
        else:
            self.cinema.setText('Все')

        i, okBtnPressed = QInputDialog.getItem(self, "Фильм",
                                               "Выберите фильм",
                                               ('', *result2),
                                               0, False)
        if okBtnPressed:
            self.film.setText(i)
        else:
            self.film.setText('Все')


class Times(QWidget):

    def __init__(self, main, film, cinema, date):
        super().__init__()
        uic.loadUi('ui_times.ui', self)

        self.con = sqlite3.connect('afisha.db')
        self.cur = self.con.cursor()

        self.cinema.setText(cinema)
        self.film.setText(film)
        self.date.setText('-'.join(reversed(date)))
        self.search(main, film, cinema, date)

    def search(self, main, film, cinema, date):
        sql1 = """SELECT DISTINCT begin, format FROM Seances WHERE film = (
        SELECT id FROM Films WHERE title = ?) and cinema = (
        SELECT id FROM Cinemas WHERE title = ?) and date = ?"""
        result1 = self.cur.execute(sql1, (film, cinema, '-'.join(date))).fetchall()

        if not result1:
            main.result.setText('По вашему запросу ничего не нашлось :(')
            QtCore.QTimer.singleShot(0, self.close)
            return

        result1.sort(key=lambda x: x[1])

        sql3 = "SELECT duration FROM Films WHERE title = ?"
        result3 = self.cur.execute(sql3, (film,)).fetchall()[0][0]

        self.time.setText(f'{result3 // 60} ч {result3 % 60} мин')
        self.table.setRowCount(0)
        for i, row in enumerate(result1):
            self.table.setRowCount(self.table.rowCount() + 1)
            for j, elem in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(elem))
        self.table.resizeColumnsToContents()


class Films(QWidget):

    def __init__(self, main, cinema, date):
        super().__init__()
        uic.loadUi('ui_films.ui', self)

        self.con = sqlite3.connect('afisha.db')
        self.cur = self.con.cursor()

        self.cinema.setText(cinema)
        self.date.setText('-'.join(reversed(date)))
        self.search(main, cinema, date)

    def search(self, main, cinema, date):
        sql2 = """SELECT DISTINCT begin, format FROM Seances WHERE cinema = (
        SELECT id FROM Cinemas WHERE title = ?) and date = ?"""
        result2 = self.cur.execute(sql2, (cinema, '-'.join(date))).fetchall()

        if not result2:
            main.result.setText('По вашему запросу ничего не нашлось :(')
            QtCore.QTimer.singleShot(0, self.close)
            return

        result = []
        for i in result2:
            time = i[0]

            sql1 = """SELECT title, duration FROM Films WHERE id in (
            SELECT film FROM Seances WHERE cinema = (
            SELECT id FROM Cinemas WHERE title = ?) and date = ? and begin = ? and format = ?)"""
            result1 = self.cur.execute(sql1, (cinema, '-'.join(date), time, i[1])).fetchall()

            for j in range(len(result1)):
                result.append((result1[j][0], time, f'{result1[j][1] // 60} ч {result1[j][1] % 60} мин', i[1]))

        result.sort(key=lambda x: x[1])

        self.table.setRowCount(0)
        for i, row in enumerate(result):
            self.table.setRowCount(self.table.rowCount() + 1)
            for j, elem in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(elem))
        self.table.resizeColumnsToContents()


class Cinemas(QWidget):

    def __init__(self, main, film, date):
        super().__init__()
        uic.loadUi('ui_cinemas.ui', self)

        self.con = sqlite3.connect('afisha.db')
        self.cur = self.con.cursor()

        self.film.setText(film)
        self.date.setText('-'.join(reversed(date)))
        self.search(main, film, date)

    def search(self, main, film, date):
        sql2 = """SELECT DISTINCT begin, format FROM Seances WHERE film = (
        SELECT id FROM Films WHERE title = ?) and date = ?"""
        result2 = self.cur.execute(sql2, (film, '-'.join(date))).fetchall()

        if not result2:
            main.result.setText('По вашему запросу ничего не нашлось :(')
            QtCore.QTimer.singleShot(0, self.close)
            return

        result = []

        sql = "SELECT duration FROM Films WHERE title = ?"
        result1 = self.cur.execute(sql, (film,)).fetchall()[0][0]

        self.time.setText(f'{result1 // 60} ч {result1 % 60} мин')

        for i in result2:
            time = i[0]

            sql3 = """SELECT title from Cinemas WHERE id in (
            SELECT cinema FROM Seances WHERE film = (
            SELECT id FROM Films WHERE title = ?) and date = ? and begin = ? and format = ?)"""
            result3 = self.cur.execute(sql3, (film, '-'.join(date), time, i[1])).fetchall()

            for j in range(len(result3)):
                result.append((result3[j][0], time, i[1]))

        result.sort(key=lambda x: x[1])

        self.table.setRowCount(0)
        for i, row in enumerate(result):
            self.table.setRowCount(self.table.rowCount() + 1)
            for j, elem in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(elem))
        self.table.resizeColumnsToContents()


class All(QWidget):

    def __init__(self, main, date):
        super().__init__()
        uic.loadUi('ui_all.ui', self)

        self.con = sqlite3.connect('afisha.db')
        self.cur = self.con.cursor()

        self.date.setText('-'.join(reversed(date)))
        self.search(main, date)

    def search(self, main, date):
        sql1 = "SELECT DISTINCT begin, format FROM Seances WHERE date = ?"
        result1 = self.cur.execute(sql1, ('-'.join(date),)).fetchall()

        if not result1:
            main.result.setText('По вашему запросу ничего не нашлось :(')
            QtCore.QTimer.singleShot(0, self.close)
            return

        result = []
        for i in result1:
            time = i[0]

            sql2 = """SELECT title FROM Cinemas WHERE id in (
            SELECT cinema FROM Seances WHERE date = ? and begin = ? and format = ?)"""
            result2 = self.cur.execute(sql2, ('-'.join(date), time, i[1])).fetchall()

            for j in result2:

                sql3 = """SELECT title, duration FROM Films WHERE id in (
                    SELECT film FROM Seances WHERE date = ? and begin = ? and format = ? and cinema = (
                    SELECT id from Cinemas WHERE title = ?))"""
                result3 = self.cur.execute(sql3, ('-'.join(date), time, i[1], j[0])).fetchall()

                for g in result3:
                    result.append((j[0], g[0], time, f'{g[1] // 60} ч {g[1] % 60} мин', i[1]))

        result.sort(key=lambda x: x[2])

        self.table.setRowCount(0)
        for i, row in enumerate(result):
            self.table.setRowCount(self.table.rowCount() + 1)
            for j, elem in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(elem))
        self.table.resizeColumnsToContents()


def get_inf(date, cinemas):

    string = f'{date[0]}-{date[1]}-{date[2]}'
    s = requests.get(f'https://www.kinopoisk.ru/afisha/city/5526/day_view/{string}/')
    b = bs4.BeautifulSoup(s.text, "html.parser")
    a = b.getText()
    a = a[a.find('список фильмов') + len('список фильмов'):a.find('фильм:')]

    with open('input.txt', 'w') as f:
        f.write(a)
    with open('input.txt') as f:
        lines = [i.strip() for i in f.readlines() if len(i.strip())]
    if lines[-1] == 'К сожалению, сеансов не найдено!Попробуйте изменить запрос.':
        return 0

    films = {}
    name = ''
    index = 1
    flag = False
    flag2 = False
    while index < len(lines):
        if flag:
            if 'мин' in lines[index] and lines[index][:lines[index].find('мин') - 1].isdigit():
                line = lines[index].split()
                films[name].append(line[0])
                flag = False
            index += 1
            continue
        else:
            for i in cinemas:
                if i == lines[index]:
                    films[name].append([lines[index]])
                    index += 1
                    flag2 = True
                    break
            if flag2:
                flag2 = False
                continue
            if '3D' in lines[index]:
                for i in range(0, len(lines[index]) - 2, 5):
                    time = lines[index][i:i + 5]
                    films[name][-1].append(time)
                films[name][-1].append('3D')
            else:
                for day in DAYS:
                    if lines[index][:len(day)] == day:
                        flag2 = True
                        break
                if flag2:
                    break
                for i in range(len(lines[index])):
                    if lines[index][i].isalpha():
                        flag2 = True
                        break
                if flag2:
                    films[lines[index]] = []
                    name = lines[index]
                    flag = True
                    index += 1
                    flag2 = False
                    continue
                for i in range(0, len(lines[index]) - 2, 5):
                    time = lines[index][i:i + 5]
                    films[name][-1].append(time)
        index += 1
    return films


def fill():

    con = sqlite3.connect('afisha.db')
    cur = con.cursor()
    sql1 = """DELETE FROM Seances"""
    sql2 = """DELETE FROM Films"""
    cur.execute(sql1)
    cur.execute(sql2)
    con.commit()

    date = str(datetime.date.today()).split('-')
    days = calendar.monthrange(int(date[0]), int(date[1]))[1]
    curr_day = int(date[2])
    curr_year = int(date[0])
    curr_month = int(date[1])
    cinemas = ['Синема Стар РИО', 'Арлекино', 'Синема Стар XXI Век Калуга',
               'Центральный', 'Инновационный культурный центр',
               'Дом Культуры «Малинники»', 'Восьмёрка (Кондрово)']

    for i in range(8):
        if curr_day > days:
            curr_month += 1
            curr_day = 1
            if curr_month > 12:
                curr_month = 1
                curr_year += 1

        result = (get_inf((curr_year, curr_month, curr_day), cinemas))

        if not result:
            break

        for j in result:
            components = result[j]

            sql = """SELECT id FROM Films WHERE title = ?"""
            result1 = cur.execute(sql, (j,)).fetchall()

            if not result1:
                sql = """INSERT INTO Films(title, duration) VALUES (?, ?)"""
                cur.execute(sql, (j, components[0]))
                con.commit()
                sql = """SELECT id FROM Films WHERE title = ?"""
                result1 = cur.execute(sql, (j,)).fetchall()[0][0]
            else:
                result1 = result1[0][0]

            film = result1
            for g in range(1, len(components)):
                cinema = components[g][0]

                sql = """SELECT id FROM Cinemas WHERE title = ?"""
                cinema = cur.execute(sql, (cinema,)).fetchall()[0][0]

                if components[g][-1] != '3D':
                    format = '2D'
                else:
                    format = '3D'

                for k in range(1, len(components[g]) - 1):
                    sql = """INSERT INTO Seances(cinema, film, date, begin, format) VALUES (?, ?, ?, ?, ?)"""
                    cur.execute(sql, (cinema, film, f'{curr_year}-{curr_month}-{curr_day}', components[g][k], format))
                    con.commit()

        curr_day += 1


if __name__ == '__main__':

    fill()

    app = QApplication(argv)
    ex = Cinema()
    ex.show()
    exit(app.exec())