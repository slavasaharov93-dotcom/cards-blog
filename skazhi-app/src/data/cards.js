// Базовый словарь карточек (демо-набор на русском языке).
// emoji используется как простая визуальная подсказка, чтобы приложение
// запускалось без бинарных картинок. В следующей версии родитель сможет
// заменить emoji на собственное фото из галереи/камеры.
//
// Каждая карточка:
//   id    — уникальный идентификатор
//   label — подпись под карточкой
//   emoji — визуальный символ
//   speak — что произносит синтезатор речи (по умолчанию = label)

export const categories = [
  {
    id: 'core',
    title: 'Главное',
    color: '#EAF3F3',
    cards: [
      { id: 'i', label: 'Я', emoji: '🙋' },
      { id: 'want', label: 'Хочу', emoji: '👉' },
      { id: 'more', label: 'Ещё', emoji: '➕' },
      { id: 'yes', label: 'Да', emoji: '✅' },
      { id: 'no', label: 'Нет', emoji: '❌' },
      { id: 'stop', label: 'Стоп', emoji: '✋' },
      { id: 'help', label: 'Помоги', emoji: '🆘', speak: 'Помоги мне' },
      { id: 'please', label: 'Пожалуйста', emoji: '🙏' },
    ],
  },
  {
    id: 'food',
    title: 'Еда',
    color: '#F3EEE6',
    cards: [
      { id: 'water', label: 'Вода', emoji: '💧' },
      { id: 'apple', label: 'Яблоко', emoji: '🍎' },
      { id: 'bread', label: 'Хлеб', emoji: '🍞' },
      { id: 'milk', label: 'Молоко', emoji: '🥛' },
      { id: 'cookie', label: 'Печенье', emoji: '🍪' },
      { id: 'banana', label: 'Банан', emoji: '🍌' },
      { id: 'eat', label: 'Есть', emoji: '🍽️', speak: 'Я хочу есть' },
      { id: 'drink', label: 'Пить', emoji: '🥤', speak: 'Я хочу пить' },
    ],
  },
  {
    id: 'feelings',
    title: 'Чувства',
    color: '#F1EEF4',
    cards: [
      { id: 'happy', label: 'Радость', emoji: '😊' },
      { id: 'sad', label: 'Грусть', emoji: '😢' },
      { id: 'angry', label: 'Злость', emoji: '😠' },
      { id: 'scared', label: 'Страх', emoji: '😨' },
      { id: 'tired', label: 'Устал', emoji: '😴' },
      { id: 'hurt', label: 'Больно', emoji: '🤕', speak: 'Мне больно' },
      { id: 'love', label: 'Люблю', emoji: '❤️' },
    ],
  },
  {
    id: 'actions',
    title: 'Действия',
    color: '#EAF1EC',
    cards: [
      { id: 'play', label: 'Играть', emoji: '🧸' },
      { id: 'walk', label: 'Гулять', emoji: '🚶' },
      { id: 'sleep', label: 'Спать', emoji: '🛏️' },
      { id: 'wash', label: 'Мыть руки', emoji: '🧼' },
      { id: 'toilet', label: 'Туалет', emoji: '🚽', speak: 'Я хочу в туалет' },
      { id: 'read', label: 'Читать', emoji: '📖' },
      { id: 'go', label: 'Идём', emoji: '🚪' },
    ],
  },
  {
    id: 'people',
    title: 'Люди',
    color: '#F4EFEA',
    cards: [
      { id: 'mom', label: 'Мама', emoji: '👩' },
      { id: 'dad', label: 'Папа', emoji: '👨' },
      { id: 'granny', label: 'Бабушка', emoji: '👵' },
      { id: 'grandpa', label: 'Дедушка', emoji: '👴' },
      { id: 'me', label: 'Я сам', emoji: '🧒' },
    ],
  },
];
