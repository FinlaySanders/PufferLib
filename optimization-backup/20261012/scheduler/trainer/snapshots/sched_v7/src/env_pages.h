#include <sys/mman.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>

static void* puf_env_array_allocate(size_t count, size_t size, int mode, size_t* mapped) {
    *mapped = 0;
    assert(mode >= 0 && mode <= 2);
    assert(size && count <= SIZE_MAX / size);
    if (!mode) return calloc(count, size);
    size_t align = 2u << 20;
    size_t bytes = (count * size + align - 1) & ~(align - 1);
    assert(bytes && bytes <= SIZE_MAX - align);
    void* raw = mmap(NULL, bytes + align, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(raw != MAP_FAILED);
    uintptr_t start = ((uintptr_t)raw + align - 1) & ~(uintptr_t)(align - 1);
    size_t prefix = start - (uintptr_t)raw;
    if (prefix) assert(munmap(raw, prefix) == 0);
    size_t suffix = align - prefix;
    if (suffix) assert(munmap((void*)(start + bytes), suffix) == 0);
    assert(madvise((void*)start, bytes, mode == 2 ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) == 0);
    *mapped = bytes;
    fprintf(stderr, "ENV_PAGES mode=%d address=%p bytes=%zu logical=%zu\n",
        mode, (void*)start, bytes, count * size);
    return (void*)start;
}

static void puf_env_array_free(void* p, size_t mapped) {
    if (mapped) assert(munmap(p, mapped) == 0);
    else free(p);
}
