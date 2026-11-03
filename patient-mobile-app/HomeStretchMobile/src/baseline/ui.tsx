import React from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
export const colors = { blue: '#367FBD', pale: '#C4DCEF', card: '#EDF3F9', ink: '#202326', muted: '#606870', line: '#B5D2EA', amber: '#FFF3D5', green: '#E5F5E9' };
export function Page({ title, children, back = true, onBack, footer }: {
    title: string;
    children: React.ReactNode;
    back?: boolean;
    onBack?: () => void;
    footer?: React.ReactNode;
}) {
    const insets = useSafeAreaInsets();
    return <View style={s.page}><View style={[s.header, { paddingTop: insets.top + 12 }]}>{back && <Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={onBack ?? (() => router.back())} style={s.back}><Ionicons name="arrow-back" color={colors.blue} size={25}/></Pressable>}<Text style={s.headerTitle}>{title}</Text></View><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={[s.body, { paddingBottom: 24 + insets.bottom }]}>{children}</ScrollView>{footer && <View style={{ padding: 16, paddingBottom: insets.bottom + 12 }}>{footer}</View>}</View>;
}
export function Button({ title, onPress, secondary = false, disabled = false, busy = false, danger = false }: {
    title: string;
    onPress: () => void;
    secondary?: boolean;
    disabled?: boolean;
    busy?: boolean;
    danger?: boolean;
}) { return <Pressable accessibilityRole="button" accessibilityState={{ disabled: disabled || busy, busy }} disabled={disabled || busy} onPress={onPress} style={({ pressed }) => [s.button, secondary && s.secondary, danger && { backgroundColor: '#DD6268', borderColor: '#DD6268' }, (disabled || busy) && { opacity: .45 }, pressed && { opacity: .75 }]}>{busy && <ActivityIndicator color={secondary ? colors.blue : '#fff'}/>}<Text style={[s.buttonText, secondary && { color: colors.blue }]}>{title}</Text></Pressable>; }
export function Card({ children }: {
    children: React.ReactNode;
}) { return <View style={s.card}>{children}</View>; }
export function Hint({ children, error = false }: {
    children: React.ReactNode;
    error?: boolean;
}) { return <View style={[s.hint, error && { backgroundColor: '#FFF0F0' }]}><Text accessibilityRole={error ? 'alert' : undefined} style={[s.small, error && { color: '#9C2028' }]}>{children}</Text></View>; }
export function Steps({ current }: {
    current: number;
}) { return <View style={s.steps}>{['Choose', 'Prepare', 'Record', 'Review'].map((label, i) => <View key={label} style={{ flex: 1, gap: 5 }}><View style={{ height: 4, borderRadius: 2, backgroundColor: i <= current ? colors.blue : colors.line }}/><Text style={{ fontSize: 11, color: i === current ? colors.blue : colors.muted }}>{label}</Text></View>)}</View>; }
export function Badge({ pending = false, active = false, saved = false }: {pending?: boolean; active?: boolean; saved?: boolean}) {
    const label = active ? '● Active baseline' : pending ? '● Awaiting review' : saved ? '● Previous baseline' : '● No baseline';
    return <View style={[s.badge, {backgroundColor: active ? colors.green : pending ? colors.amber : '#E6EDF3'}]}><Text style={{fontSize:12,color:active?'#246B3C':pending?'#865600':colors.muted}}>{label}</Text></View>;
}
export function Choice<T extends string>({ label, value, options, onChange }: {
    label: string;
    value: T;
    options: {
        value: T;
        label: string;
    }[];
    onChange: (value: T) => void;
}) { return <View style={{ gap: 8, marginBottom: 16 }}><Text style={s.title}>{label}</Text><View style={s.choices}>{options.map(option => <Pressable key={option.value} accessibilityRole="radio" accessibilityState={{ checked: option.value === value }} onPress={() => onChange(option.value)} style={[s.choice, option.value === value && { backgroundColor: colors.blue }]}><Text style={{ color: option.value === value ? '#fff' : colors.blue, fontWeight: '600' }}>{option.label}</Text></Pressable>)}</View></View>; }
export const s = StyleSheet.create({ page: { flex: 1, backgroundColor: '#fff' }, header: { backgroundColor: colors.pale, paddingHorizontal: 50, paddingBottom: 18, minHeight: 88, justifyContent: 'flex-end' }, headerTitle: { fontSize: 23, color: colors.blue, fontWeight: '600', textAlign: 'center' }, back: { position: 'absolute', bottom: 12, left: 10, padding: 10 }, body: { padding: 16, gap: 12 }, card: { backgroundColor: colors.card, borderRadius: 15, padding: 16, gap: 8 }, title: { fontSize: 17, fontWeight: '600', color: colors.ink }, text: { fontSize: 15, lineHeight: 22, color: colors.ink }, small: { fontSize: 13, lineHeight: 19, color: colors.muted }, button: { minHeight: 50, borderRadius: 12, padding: 12, backgroundColor: colors.blue, borderWidth: 1, borderColor: colors.blue, justifyContent: 'center', alignItems: 'center', flexDirection: 'row', gap: 8, marginTop: 4 }, secondary: { backgroundColor: '#fff' }, buttonText: { fontSize: 16, fontWeight: '600', color: '#fff', textAlign: 'center' }, hint: { backgroundColor: '#DCEAF7', padding: 13, borderRadius: 12 }, steps: { flexDirection: 'row', gap: 5, marginBottom: 8 }, badge: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 12, alignSelf: 'flex-start' }, input: { minHeight: 48, borderWidth: 1, borderColor: colors.line, borderRadius: 10, padding: 12, fontSize: 16, color: colors.ink, backgroundColor: '#fff' }, choices: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' }, choice: { minHeight: 44, borderWidth: 1, borderColor: colors.line, borderRadius: 10, padding: 12, justifyContent: 'center' }, row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }, circle: { width: 170, height: 170, borderRadius: 85, borderWidth: 7, borderColor: colors.blue, backgroundColor: colors.card, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginVertical: 20 } });
