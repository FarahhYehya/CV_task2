/* Number fields for a list of options (options.js). Values stay strings, "" = optional field not sent. */
export default function OptionsForm({ options, values, onChange, disabled = false }) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-2">
      {options.map((option) => (
        <label key={option.name} className="text-sm">
          <span className="block font-medium text-slate-700">{option.label}</span>
          <input
            type="number"
            className="input"
            value={values[option.name]}
            min={option.min}
            max={option.max}
            step={option.step ?? (option.type === "int" ? 1 : "any")}
            disabled={disabled}
            onChange={(e) => onChange(option.name, e.target.value)}
          />
          <span className="text-xs text-slate-400">{option.unit}</span>
        </label>
      ))}
    </div>
  );
}
