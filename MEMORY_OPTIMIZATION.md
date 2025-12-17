# Optymalizacja Pamięci dla Fly.io

## Problem
Bot był zabijany przez OOM Killer na Fly.io z powodu zbyt dużego zużycia pamięci (~140MB RSS, 809MB wirtualnej).

## Implementowane Rozwiązania

### 1. Zwiększenie Pamięci RAM (fly.toml)
- **Przed**: `shared-cpu-1x` (~256MB RAM)
- **Po**: `shared-cpu-2x` z `memory = '512mb'`
- **Efekt**: Podwojenie dostępnej pamięci

### 2. Ograniczenie Pobierania Historii
- **Przed**: `channel.history(limit=500)` - 500 wiadomości
- **Po**: `channel.history(limit=100)` - 100 wiadomości
- **Efekt**: 5x mniej obiektów wiadomości w pamięci

### 3. LRU Cache dla IID
- **Przed**: Nieograniczony `set()` - rósł w nieskończoność
- **Po**: `LRUCache(maxsize=5000)` z automatycznym usuwaniem najstarszych
- **Implementacja**: `collections.OrderedDict` z limitem 5000 wpisów
- **Efekt**: Stały rozmiar cache ~200-300KB

### 4. Batch Processing
- **Przed**: Wszystkie wiadomości przetwarzane naraz
- **Po**: Przetwarzanie w batch'ach po 20 wiadomości
- **Efekt**: Liniowe zużycie pamięci zamiast ładowania wszystkiego naraz

### 5. Garbage Collection
- Wywołanie `gc.collect()` po zakończeniu synchronizacji
- Czyszczenie list `batch.clear()`, `all_messages.clear()`, `messages_to_process.clear()`
- **Efekt**: Natychmiastowe zwolnienie pamięci po dużych operacjach

## Spodziewane Wyniki
- **Zmniejszenie zużycia pamięci o ~60-70%**
- **Stabilna praca bota bez OOM kills**
- **Szybsze działanie cache (LRU jest bardziej wydajny)**

## Monitoring
Sprawdź logi Fly.io aby zweryfikować:
```bash
fly logs
fly status
fly vm status
```

## Deploy
```bash
fly deploy
```

## Dodatkowe Opcje (jeśli nadal są problemy)

### A. Jeszcze bardziej ograniczyć limit
```python
async for message in channel.history(limit=50):  # zmniejsz z 100 na 50
```

### B. Zwiększyć do shared-cpu-4x
```toml
[[vm]]
  size = 'shared-cpu-4x'
  memory = '1024mb'
```

### C. Dodać swap
```toml
[env]
  SWAP_SIZE_MB = "512"
```

### D. Wyłączyć synchronizację przy starcie
Jeśli bot nie potrzebuje synchronizacji przy każdym starcie, można uruchamiać ją ręcznie przez komendę.
