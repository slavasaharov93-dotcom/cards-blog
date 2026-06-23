// Спокойная, неяркая палитра — важно для пользователей с РАС:
// мягкие тона, высокий контраст текста, крупные элементы, минимум визуального шума.
export const theme = {
  colors: {
    background: '#F4F1EA',
    surface: '#FFFFFF',
    text: '#2B2B2B',
    textMuted: '#6B6B6B',
    border: '#E2DCD0',
    primary: '#3E7C7B',
    primaryText: '#FFFFFF',
    danger: '#C9594F',
  },
  // Крупные размеры — карточки легко нажимать, в т.ч. при моторных трудностях.
  card: {
    minHeight: 120,
    radius: 18,
    gap: 12,
  },
  font: {
    label: 20,
    big: 26,
  },
};
