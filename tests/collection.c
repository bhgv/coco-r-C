/* Stable addresses must survive growth, including growth from callbacks. */
#include "collect.h"
static Collection records;
static void grow(void *record)
{
    int value = *(int *)record;
    Collection_New(&records);
    *(int *)record = value + 1;
}
int main(void)
{
    int i, *first;
    Collection_Init(&records, sizeof(int), 1, 1);
    Collection_New(&records);
    first = Collection_At(&records, 0);
    *first = 17;
    for (i = 1; i < 5000; ++i) Collection_New(&records);
    if (Collection_At(&records, 0) != first || *first != 17) return 1;
    *first = 42;
    if (*(int *)Collection_At(&records, 0) != 42) return 2;
    if (Collection_At(&records, -1) || Collection_At(&records, 5000)) return 3;
    Collection_ForEach(&records, grow);
    if (Collection_Count(&records) != 10000 || *first != 43) return 4;
    Collection_Clean(&records);
    Collection_New(&records);
    if (Collection_At(&records, 0) != first || *first != 0) return 5;
    Collection_Done(&records);
    return 0;
}
