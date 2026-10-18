/* Stable-address record collection. Growing the pointer table never relocates records. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include "collect.h"

/* Fail before modifying a live collection on an invalid size or allocation failure. */
static void Collection_Panic(const char *operation)
{
    fprintf(stderr, "%s: invalid size, index, or out of memory\n", operation);
    exit(1);
}

/* Reserve zeroed pointer slots; actual records are allocated only when first used. */
void Collection_Init(PCollection col, int element_size, int capacity, int extend)
{
    if (element_size <= 0 || capacity <= 0 || extend <= 0 ||
        (size_t)capacity > (size_t)-1 / sizeof(char *))
        Collection_Panic("Collection.init");
    col->data = (char **)calloc((size_t)capacity, sizeof(char *));
    if (!col->data) Collection_Panic("Collection.init");
    col->el_size = element_size;
    col->n_ext = extend;
    col->size = capacity;
    col->el_free = 0;
}

/* Release every allocated record and the table, but not pointers owned by record fields. */
void Collection_Done(PCollection col)
{
    int i;
    for (i = 0; i < col->size; ++i) free(col->data[i]);
    free(col->data);
    col->data = NULL;
    col->size = col->el_free = 0;
}

/* Keep record capacity for reuse; Collection_New reinitializes each returned record. */
void Collection_Clean(PCollection col)
{
    col->el_free = 0;
}

/* Grow only the pointer table, preserving all record addresses and edits through old pointers. */
static void Collection_Resize(PCollection col)
{
    int capacity;
    char **table;
    if (col->size > INT_MAX - col->n_ext) Collection_Panic("Collection.resize");
    capacity = col->size + col->n_ext;
    if ((size_t)capacity > (size_t)-1 / sizeof(char *)) Collection_Panic("Collection.resize");
    table = (char **)realloc(col->data, (size_t)capacity * sizeof(char *));
    if (!table) Collection_Panic("Collection.resize");
    memset(table + col->size, 0, (size_t)(capacity - col->size) * sizeof(char *));
    col->data = table;
    col->size = capacity;
}

/* Return a newly zeroed, stable record index. */
int Collection_New(PCollection col)
{
    int index = col->el_free;
    if (index == col->size) Collection_Resize(col);
    if (!col->data[index]) col->data[index] = (char *)malloc((size_t)col->el_size);
    if (!col->data[index]) Collection_Panic("Collection.new");
    memset(col->data[index], 0, (size_t)col->el_size);
    ++col->el_free;
    return index;
}

/* Return the live record count, excluding reserved capacity. */
int Collection_Count(PCollection col)
{
    return col->el_free;
}

/* Reject negative and one-past-live indexes instead of returning an invalid record. */
void *Collection_At(PCollection col, int index)
{
    if (index < 0 || index >= col->el_free) return NULL;
    return col->data[index];
}

/* Copy a valid record into caller-owned storage. */
void Collection_Get(PCollection col, int index, void *out)
{
    void *record = Collection_At(col, index);
    if (!record || !out) Collection_Panic("Collection.get");
    memcpy(out, record, (size_t)col->el_size);
}

/* Replace a valid record without changing its address. */
void Collection_Put(PCollection col, int index, void *value)
{
    void *record = Collection_At(col, index);
    if (!record || !value) Collection_Panic("Collection.put");
    memcpy(record, value, (size_t)col->el_size);
}

/* Iterate only the records live at entry; callbacks may safely grow the collection. */
void Collection_ForEach(PCollection col, Collection_Func function)
{
    int i, count = col->el_free;
    for (i = 0; i < count; ++i) function(col->data[i]);
}

/* As above, also pass the stable index to the callback. */
void Collection_ForEachPos(PCollection col, Collection_FuncPos function)
{
    int i, count = col->el_free;
    for (i = 0; i < count; ++i) function(col->data[i], i);
}

/* Return the first matching live index, or -1. */
int Collection_FirstThat(PCollection col, Collection_Comp function, void *value)
{
    int i, count = col->el_free;
    for (i = 0; i < count; ++i)
        if (function(col->data[i], value)) return i;
    return -1;
}
