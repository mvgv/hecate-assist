CREATE TABLE IF NOT EXISTS pacientes (
  id TEXT PRIMARY KEY,              -- "P001"
  nome TEXT NOT NULL,               -- ficticio
  data_nascimento TEXT NOT NULL,    -- ISO
  sexo TEXT CHECK (sexo IN ('M','F','O')),
  comorbidades TEXT NOT NULL DEFAULT '[]',   -- JSON array de strings
  medicacoes_em_uso TEXT NOT NULL DEFAULT '[]',
  criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alergias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  substancia TEXT NOT NULL,         -- ex.: "penicilina"
  gravidade TEXT CHECK (gravidade IN ('leve','moderada','grave'))
);

CREATE TABLE IF NOT EXISTS exames (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  tipo TEXT NOT NULL,               -- ex.: "potassio_serico"
  status TEXT NOT NULL CHECK (status IN ('pendente','concluido')),
  resultado REAL,                   -- NULL se pendente
  unidade TEXT,
  faixa_critica_min REAL,           -- fora de [min,max] => critico
  faixa_critica_max REAL,
  solicitado_em TEXT NOT NULL,
  concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS alertas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paciente_id TEXT NOT NULL REFERENCES pacientes(id),
  tipo TEXT NOT NULL,               -- 'exame_critico' | 'sugestao_tratamento'
  severidade TEXT NOT NULL CHECK (severidade IN ('info','atencao','critico')),
  mensagem TEXT NOT NULL,
  aprovado_por TEXT,
  criado_em TEXT DEFAULT (datetime('now'))
);

-- SQLite nao permite expressoes em UNIQUE de tabela; usa-se indice unico com
-- expressao para obter a mesma idempotencia diaria (paciente_id, tipo, dia).
CREATE UNIQUE INDEX IF NOT EXISTS idx_alertas_idempotencia_diaria
  ON alertas (paciente_id, tipo, date(criado_em));
