import React from 'react';
import { View, Pressable, Text, ScrollView, StyleSheet } from 'react-native';
import { theme } from '../theme';

// Верхняя полоска: собранная из карточек фраза + кнопки «Сказать» и «Очистить».
export default function PhraseBar({ items, onSpeak, onClear, onRemoveLast }) {
  const isEmpty = items.length === 0;
  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={onRemoveLast}
        disabled={isEmpty}
        style={styles.strip}
        accessibilityLabel="Собранная фраза. Нажмите, чтобы удалить последнюю карточку."
      >
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.stripContent}
        >
          {isEmpty ? (
            <Text style={styles.placeholder}>Нажимай на карточки…</Text>
          ) : (
            items.map((it, idx) => (
              <View key={`${it.id}-${idx}`} style={styles.chip}>
                <Text style={styles.chipEmoji}>{it.emoji}</Text>
                <Text style={styles.chipLabel}>{it.label}</Text>
              </View>
            ))
          )}
        </ScrollView>
      </Pressable>

      <View style={styles.actions}>
        <Pressable
          onPress={onSpeak}
          disabled={isEmpty}
          style={[styles.btn, styles.speak, isEmpty && styles.btnDisabled]}
          accessibilityRole="button"
          accessibilityLabel="Сказать фразу вслух"
        >
          <Text style={styles.speakText}>🔊 Сказать</Text>
        </Pressable>
        <Pressable
          onPress={onClear}
          disabled={isEmpty}
          style={[styles.btn, styles.clear, isEmpty && styles.btnDisabled]}
          accessibilityRole="button"
          accessibilityLabel="Очистить фразу"
        >
          <Text style={styles.clearText}>Очистить</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 12,
    gap: 10,
  },
  strip: {
    minHeight: 66,
    borderRadius: 14,
    backgroundColor: theme.colors.background,
    borderWidth: 1,
    borderColor: theme.colors.border,
    justifyContent: 'center',
  },
  stripContent: {
    alignItems: 'center',
    paddingHorizontal: 10,
    gap: 8,
  },
  placeholder: {
    color: theme.colors.textMuted,
    fontSize: 17,
  },
  chip: {
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  chipEmoji: { fontSize: 28 },
  chipLabel: { fontSize: 14, fontWeight: '600', color: theme.colors.text },
  actions: {
    flexDirection: 'row',
    gap: 10,
  },
  btn: {
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  speak: {
    flex: 2,
    backgroundColor: theme.colors.primary,
  },
  clear: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  speakText: {
    color: theme.colors.primaryText,
    fontSize: theme.font.big,
    fontWeight: '700',
  },
  clearText: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: '600',
  },
});
