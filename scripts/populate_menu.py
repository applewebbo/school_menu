import csv

from school_menu.models import DetailedMeal


def run():
    with open("data/menu_scuola.csv") as file:
        reader = csv.reader(file)
        next(reader)

        DetailedMeal.objects.all().delete()

        for row in reader:
            print(row)

            meal = DetailedMeal(
                type=row[0],
                season=row[1],
                week=row[2],
                day=row[3],
                first_course=row[4],
                second_course=row[5],
                side_dish=row[6],
                fruit=row[7],
                snack=row[8],
                school=row[9],
            )

            meal.save()
