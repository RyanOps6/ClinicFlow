import sys, os, json
sys.path.insert(0, "D:\\iclinic\\clinicflow\\backend")
os.chdir("D:\\iclinic\\clinicflow\\backend")

from app.llm.client import llm_client

# Test 1: basic chat (no response_format)
r1 = llm_client.chat([
    {"role": "system", "content": "Say hello in one word."},
    {"role": "user", "content": "hi"}
])
print("TEST1 (no format):", repr(r1))

# Test 2: json response format  
r2 = llm_client.chat([
    {"role": "system", "content": "Return JSON with a 'name' field."},
    {"role": "user", "content": "My name is John"}
], response_format={"type": "json_object"})
print("TEST2 (json):", repr(r2))

# Test 3: extract_json
r3 = llm_client.extract_json([
    {"role": "system", "content": "Return JSON with a 'name' field."},
    {"role": "user", "content": "My name is John"}
])
print("TEST3 (extract):", repr(r3))
