---
title: "React Component Architecture Patterns for Frontend Engineers"
type: guide
domain: frontend-engineering
level: intermediate
status: active
version: v1.0
tags: [react, component-architecture, frontend, patterns, typescript]
related:
  - "[[Web_Performance_Optimization_Strategies]]"
  - "[[Backend_Service_Architecture_FastAPI]]"
  - "[[Technical_Documentation_Standards]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to React component architecture patterns for frontend engineers — covering component composition, state management, data fetching, and scalable project organization.

## Prerequisites

- React 18+ fundamentals
- TypeScript basics
- Familiarity with hooks

## Pattern 1: Compound Components

Components that share state through context without prop drilling:

```tsx
// Compound component pattern
const Select = ({ children, value, onChange }: SelectProps) => {
  return (
    <SelectContext.Provider value={{ value, onChange }}>
      <div className="select">{children}</div>
    </SelectContext.Provider>
  );
};

Select.Option = function Option({ value, children }: OptionProps) {
  const { value: selected, onChange } = useSelectContext();
  return (
    <div
      className={`option ${value === selected ? "selected" : ""}`}
      onClick={() => onChange(value)}
    >
      {children}
    </div>
  );
};

// Usage
<Select value={status} onChange={setStatus}>
  <Select.Option value="active">Active</Select.Option>
  <Select.Option value="archived">Archived</Select.Option>
</Select>
```

## Pattern 2: Container/Presentational Split

Separate data fetching from rendering:

```tsx
// Container (data fetching)
function OrderListContainer() {
  const { data: orders, isLoading, error } = useOrders();
  if (isLoading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  return <OrderList orders={orders} />;
}

// Presentational (pure rendering)
function OrderList({ orders }: { orders: Order[] }) {
  return (
    <ul>
      {orders.map(order => (
        <OrderItem key={order.id} order={order} />
      ))}
    </ul>
  );
}
```

## Pattern 3: Custom Hooks for Business Logic

Extract complex logic from components:

```tsx
function useOrders(filters?: OrderFilters) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    fetchOrders(filters)
      .then(setOrders)
      .catch(setError)
      .finally(() => setIsLoading(false));
  }, [filters]);

  return { orders, isLoading, error };
}
```

## Pattern 4: Render Props / Children as Function

```tsx
function DataProvider<T>({
  fetchFn,
  children,
}: {
  fetchFn: () => Promise<T>;
  children: (state: { data: T | null; loading: boolean }) => ReactNode;
}) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  // ... fetch logic
  return <>{children({ data, loading })}</>;
}
```

## State Management Decision Tree

```
Local component state?
  → useState / useReducer

Shared between siblings?
  → Lift state up / context

Server state (API data)?
  → React Query / SWR

Global UI state?
  → Zustand / Jotai

Complex domain state?
  → Redux Toolkit (if team is familiar)
```

## Project Structure

```
src/
├── components/           # Shared UI components
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
├── features/             # Feature-based modules
│   └── orders/
│       ├── components/
│       ├── hooks/
│       ├── api.ts
│       └── types.ts
├── hooks/                # Shared custom hooks
├── lib/                  # Third-party wrappers
└── types/                # Global type definitions
```

## Performance Patterns

```tsx
// Memoize expensive components
const ExpensiveList = React.memo(({ items }) => (
  <ul>{items.map(item => <Item key={item.id} item={item} />)}</ul>
));

// Memoize callbacks
const handleClick = useCallback((id: string) => {
  setSelected(id);
}, []);

// Memoize expensive computations
const sortedItems = useMemo(
  () => items.sort((a, b) => a.name.localeCompare(b.name)),
  [items]
);
```

## Conclusion

Compound components for complex UI state sharing, container/presentational split for testability, and custom hooks for business logic reuse are the foundation of scalable React architecture. Use React Query for server state — avoid lifting server state into Redux.
