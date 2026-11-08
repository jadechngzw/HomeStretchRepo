import { useCallback, useEffect, useState } from 'react';
import { AppState } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useCatalog } from './store';
import { dailySurvey, localDay } from './dailySurveys';

export function useDailySurveys() {
  const catalog = useCatalog();
  const [day, setDay] = useState(localDay);
  const refresh = useCallback(() => setDay(localDay()), []);
  useFocusEffect(refresh);
  useEffect(() => {
    const listener = AppState.addEventListener('change', refresh);
    const now = new Date();
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const timer = setTimeout(refresh, midnight.getTime() - now.getTime() + 100);
    return () => { listener.remove(); clearTimeout(timer); };
  }, [refresh, day]);
  return { before: dailySurvey(catalog.data, 'before', day), after: dailySurvey(catalog.data, 'after', day) };
}
