import React from 'react';
import { Pressable, Text, StyleSheet } from 'react-native';
import { theme } from '../theme';

// Одна карточка. По нажатию озвучивает себя и добавляется в полоску фразы.
export default function CardTile({ card, backgroundColor, onPress }) {
  return (
    <Pressable
      onPress={() => onPress(card)}
      style={({ pressed }) => [
        styles.tile,
        { backgroundColor: backgroundColor || theme.colors.surface },
        pressed && styles.pressed,
      ]}
      accessibilityRole="button"
      accessibilityLabel={card.label}
    >
      <Text style={styles.emoji}>{card.emoji}</Text>
      <Text style={styles.label} numberOfLines={2}>
        {card.label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minHeight: theme.card.minHeight,
    borderRadius: theme.card.radius,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
  },
  pressed: {
    opacity: 0.6,
    transform: [{ scale: 0.97 }],
  },
  emoji: {
    fontSize: 44,
    marginBottom: 6,
  },
  label: {
    fontSize: theme.font.label,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
  },
});
