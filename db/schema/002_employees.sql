CREATE TABLE [{{schema}}].[employees] (
    employee_id BIGINT IDENTITY(1,1) NOT NULL,
    employee_code NVARCHAR(30) NOT NULL,
    full_name NVARCHAR(160) NOT NULL,
    role NVARCHAR(40) NOT NULL,
    is_active BIT NOT NULL CONSTRAINT DF_employees_is_active DEFAULT (1),
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_employees_created_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_employees PRIMARY KEY (employee_id),
    CONSTRAINT UQ_employees_employee_code UNIQUE (employee_code)
)
