from pydantic import BaseModel, ConfigDict
class MyModel(BaseModel):
    id: int

m = MyModel(id=1)
try:
    m.distance = 5.0
    print("Direct set works")
except Exception as e:
    print(f"Direct set failed: {e}")

object.__setattr__(m, 'distance', 5.0)
print(f"Bypass works, getattr: {getattr(m, 'distance')}")
