from ..models import Competition, Participant, DisciplineCategory, AgeCategory, Performance


def write_competitions(competitions):
    for competition in competitions:
        print(competition)
        Competition.objects.create(
            name=competition['name'],
            sity=competition['city'],
            start_date=competition['start_date'],
            end_date=competition['end_date'],
            link=competition['link']
        )