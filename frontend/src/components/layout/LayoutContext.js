import { createContext, useContext } from "react";

export const LayoutContext = createContext({
  collapsed: false,
  mobileOpen: false,
  toggleCollapsed: () => {},
  openMobile: () => {},
  closeMobile: () => {}
});

export function useLayout() {
  return useContext(LayoutContext);
}
