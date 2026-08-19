import { Languages } from "lucide-react";
import { SUPPORTED_LANGUAGES } from "../lib/languages";

export default function LanguageSelect({ value, onChange, disabled }) {
  return (
    <label className="flex items-center gap-2 text-xs font-medium text-navy-500">
      <Languages className="h-4 w-4 text-navy-400" />
      <span className="hidden sm:inline">Response language</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-sm2 border border-navy-200 bg-white px-2 py-1.5 text-sm text-ink
          focus:border-navy-400 disabled:opacity-50"
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </label>
  );
}
