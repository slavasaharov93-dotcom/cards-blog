import React, { useMemo, useState } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  FlatList,
  StyleSheet,
  Platform,
  StatusBar as RNStatusBar,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as Speech from 'expo-speech';

import { categories } from './src/data/cards';
import { theme } from './src/theme';
import CardTile from './src/components/CardTile';
import CategoryTabs from './src/components/CategoryTabs';
import PhraseBar from './src/components/PhraseBar';

const NUM_COLUMNS = 3;

export default function App() {
  const [activeCategoryId, setActiveCategoryId] = useState(categories[0].id);
  const [phrase, setPhrase] = useState([]);

  const activeCategory = useMemo(
    () => categories.find((c) => c.id === activeCategoryId) || categories[0],
    [activeCategoryId]
  );

  // Произнести произвольный текст по-русски (offline TTS устройства).
  const say = (text) => {
    Speech.stop();
    Speech.speak(text, { language: 'ru-RU', rate: 0.95, pitch: 1.0 });
  };

  // Тап по карточке: озвучить и добавить в фразу.
  const handleCardPress = (card) => {
    say(card.speak || card.label);
    setPhrase((prev) => [...prev, card]);
  };

  const handleSpeakPhrase = () => {
    if (phrase.length === 0) return;
    const text = phrase.map((c) => c.speak || c.label).join(' ');
    say(text);
  };

  const handleClear = () => setPhrase([]);
  const handleRemoveLast = () => setPhrase((prev) => prev.slice(0, -1));

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />

      <View style={styles.header}>
        <Text style={styles.title}>Скажи</Text>
      </View>

      <PhraseBar
        items={phrase}
        onSpeak={handleSpeakPhrase}
        onClear={handleClear}
        onRemoveLast={handleRemoveLast}
      />

      <CategoryTabs
        categories={categories}
        activeId={activeCategoryId}
        onSelect={setActiveCategoryId}
      />

      <FlatList
        data={activeCategory.cards}
        keyExtractor={(item) => item.id}
        numColumns={NUM_COLUMNS}
        contentContainerStyle={styles.grid}
        columnWrapperStyle={styles.gridRow}
        renderItem={({ item }) => (
          <CardTile
            card={item}
            backgroundColor={activeCategory.color}
            onPress={handleCardPress}
          />
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: theme.colors.background,
    paddingTop: Platform.OS === 'android' ? RNStatusBar.currentHeight : 0,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: theme.colors.primary,
    letterSpacing: 0.5,
  },
  grid: {
    padding: theme.card.gap,
    gap: theme.card.gap,
  },
  gridRow: {
    gap: theme.card.gap,
  },
});
