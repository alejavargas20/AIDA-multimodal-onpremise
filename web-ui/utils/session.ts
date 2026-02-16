// aida-multimodal-onpremise/web-ui/utils/session.ts
import { User } from "@/types/user";

const KEY = "aida_user";

export const saveUser = (user: User) => {
  localStorage.setItem(KEY, JSON.stringify(user));
};

export const loadUser = (): User | null => {
  const raw = localStorage.getItem(KEY);
  return raw ? JSON.parse(raw) : null;
};

export const clearUser = () => {
  localStorage.removeItem(KEY);
};
