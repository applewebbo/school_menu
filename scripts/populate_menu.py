import csv
from calendar import week

from school_menu.models import Meal


def run():
    with open("data/menu_scuola.csv") as file:
        reader = csv.reader(file)
        next(reader)

        Meal.objects.all().delete()

        for row in reader:
            print(row)

            meal = Meal(
                season=row[0],
                week=row[1],
                day=row[2],
                first_course=row[3],
                second_course=row[4],
                side_dish=row[5],
                fruit=row[6],
                snack=row[7],
            )

            meal.save()
