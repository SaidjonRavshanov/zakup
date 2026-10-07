/** Field yorlig'i bog'lanadigan boshqaruv elementlari (id — ichki <input>/<select> ga tushadi). */
export const LABELLABLE = new Set<unknown>(['input', 'select', 'textarea'])

/** Shu yorliq bilan bog'lanadigan komponent (o'z `id` propini ichki inputga uzatishi kerak). */
export function labellable<T>(component: T): T {
  LABELLABLE.add(component)
  return component
}
