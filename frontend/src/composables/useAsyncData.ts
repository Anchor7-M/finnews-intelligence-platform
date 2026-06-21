import { onMounted, ref } from "vue";

export function useAsyncData<T>(loader: () => Promise<T>) {
  const data = ref<T | null>(null);
  const error = ref<string | null>(null);
  const loading = ref(true);

  onMounted(async () => {
    try {
      data.value = await loader();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Unknown error";
    } finally {
      loading.value = false;
    }
  });

  return { data, error, loading };
}
