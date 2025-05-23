from flask import Flask, request, jsonify
import logging
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': (['1540737/daa6e420d33102bf6947', '213044/7df73ae4cc715175059e'], ('россия')),
    'нью-йорк': (['1652229/728d5c86707054d4745f', '1030494/aca7ed7acefde2606bdc'], ('соединенные штаты америки', 'америка', 'штаты', 'сша')),
    'париж': (["1652229/f77136c2364eb90a3ea8", '123494/aca7ed7acefd12e606bdc'], ('франция'))
}

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False
        }
        return

    if 'помощь' in req['request']['nlu']['tokens']:
        res['response']['text'] = 'Это игра "Отгадай город".\n'\
                                  'Ваша задача - отгадать три загаданных города по их картинкам.\n'\
                                  'Если вы ошибётесь один раз, я дам вам подсказку - ещё одну картинку.\n'\
                                  'Если вы снова не отгадаетё, я скажу что это за город и перейду к следующему.\n'\
                                  'После города, я спрошу у вас страну, в которой этот город находится, будьте внимательны - у вас всего одна попытка!'

    elif sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                }
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    res['response']['text'] = 'Ты отгадал все города!'
                    res['response']['end_session'] = True
                else:
                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['attempt'] = 1
                    sessionStorage[user_id]['country'] = 0
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['response']['end_session'] = True
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ]
        else:
            play_game(res, req)

    help = {
        'title': 'Помощь',
        'hide': True
    }

    if 'buttons' in res['response']:
        res['response']['buttons'].append(help)
    
    else:
        res['response']['buttons'] = [help]


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:
        city = random.choice(list(cities))
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))
        sessionStorage[user_id]['city'] = city
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][0][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
    else:
        city = sessionStorage[user_id]['city']
        if sessionStorage[user_id]['country'] == 1:
            if get_country(req) in cities[city][1]:
                res['response']['text'] = 'Правильно! Cыграем ещё?'
            else:
                res['response']['text'] = f'Неправильно, правильный ответ - {cities[city][1][0].capitalize()}.\nСыграем ещё?' 

            sessionStorage[user_id]['game_started'] = False
            sessionStorage[user_id]['country'] = 0
            sessionStorage[user_id]['guessed_cities'].append(city)
            res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    },
                    {
                        'title': 'Покажи город на карте',
                        'hide': True,
                        'url': f'https://yandex.ru/maps/?mode=search&text={city}'
                    }
                ]
            return

        else:
            if get_city(req) == city:
                res['response']['text'] = 'Правильно! А в какой стране этот город?'
                sessionStorage[user_id]['country'] = 1
            else:
                if attempt == 3:
                    res['response']['text'] = f'Вы пытались. Это {city.title()}. А вы знаете в какой стране этот город?'
                    sessionStorage[user_id]['country'] = 1
                else:
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                    res['response']['card']['image_id'] = cities[city][0][attempt - 1]
                    res['response']['text'] = 'А вот и не угадал!'
    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('city', None)


def get_country(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('country', None)


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
       if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()