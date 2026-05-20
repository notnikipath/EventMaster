import React from "react";
import { SafeAreaView, ScrollView, Text, View } from "react-native";

export default function App() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#f2f7f4" }}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 16 }}>
        <Text style={{ fontSize: 30, fontWeight: "700", color: "#13233a" }}>EventMaster Mobile</Text>
        <Text style={{ color: "#53657a" }}>
          Приложение участника: программа мероприятия, карта площадки, статус билета и быстрый check-in.
        </Text>
        <View style={{ backgroundColor: "white", borderRadius: 16, padding: 14 }}>
          <Text style={{ fontWeight: "600", marginBottom: 8 }}>Экран программы</Text>
          <Text style={{ color: "#53657a" }}>Секции по времени, фильтр по трекам и пуш-напоминания.</Text>
        </View>
        <View style={{ backgroundColor: "white", borderRadius: 16, padding: 14 }}>
          <Text style={{ fontWeight: "600", marginBottom: 8 }}>Экран навигации</Text>
          <Text style={{ color: "#53657a" }}>Интерактивная карта зала, поиск стендов, точки check-in.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
