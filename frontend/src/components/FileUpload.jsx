import React from 'react'

export default function FileUpload({ onFileSelect }) {
  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file && onFileSelect) {
      onFileSelect(file)
    }
  }

  return (
    <div>
      <label htmlFor="file-input">Upload file</label>
      <input
        id="file-input"
        type="file"
        onChange={handleChange}
        data-testid="file-input"
      />
    </div>
  )
}
