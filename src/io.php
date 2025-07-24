<?php

declare(strict_types=1);

namespace Infoclimat\IO;

use Exception;
use PDO;

/**
 * @throws Exception
 */
function load_pdo_ip(): string|array
{
    $ip = getenv('DB_HOST');
    if (empty($ip)) {
        throw new Exception('Missing DB_HOST in environment variables');
    }
    return $ip;
}

/**
 * @throws Exception
 */
function load_pdo_username(): string|array
{
    $username = getenv('DB_USER');
    if (empty($username)) {
        throw new Exception('Missing DB_USER in environment variables');
    }
    return $username;
}

/**
 * @throws Exception
 */
function load_pdo_password(): string|array
{
    $password = getenv('DB_PASSWORD');
    if (empty($password)) {
        throw new Exception('Missing DB_PASSWORD in environment variables');
    }
    return $password;
}

/**
 * @throws Exception
 */
function load_pdo_config(): array
{
    $ip = load_pdo_ip();
    $username = load_pdo_username();
    $password = load_pdo_password();
    return [$ip, $username, $password];
}

/**
 * @throws Exception
 */
function connexion_sql(string $db): PDO
{
    [$ip, $username, $password] = load_pdo_config();
    return new PDO(
        "mysql:host={$ip};dbname={$db}",
        $username,
        $password
    );
}

interface CommandExecutor
{
    public function exec(string $command): false|string;

    public function shell_exec(string $command): false|string|null;

    public function passthru(string $command): ?false;

    public function system(string $command): false|string;
}

class RealCommandExecutor implements CommandExecutor
{
    public function exec(string $command): false|string
    {
        return exec($command);
    }

    public function shell_exec(string $command): false|string|null
    {
        return shell_exec($command);
    }

    public function passthru(string $command): ?false
    {
        return passthru($command);
    }

    public function system(string $command): false|string
    {
        return system($command);
    }
}

class FakeCommandExecutor implements CommandExecutor
{
    /**
     * @var string[]
     */
    public array $commands = [];

    public function exec(string $command): false|string
    {
        $this->commands[] = $command;
        return false; // TODO
    }

    public function shell_exec(string $command): false|string|null
    {
        $this->commands[] = $command;
        return null; // TODO
    }

    public function passthru(string $command): ?false
    {
        $this->commands[] = $command;
        return null;
    }

    public function system(string $command): false|string
    {
        $this->commands[] = $command;
        return false; // TODO
    }
}

interface Outputer
{
    public function echo(string $str): void;

    public function print_r(mixed $value): void;
}

class RealOutputer implements Outputer
{
    public function echo(string $str): void
    {
        echo $str;
    }

    public function print_r(mixed $value): void
    {
        print_r($value);
    }
}

class FakeOutputer implements Outputer
{
    public string $output = '';

    public function echo(string $str): void
    {
        $this->output .= $str;
    }

    public function print_r(mixed $value): void
    {
        $this->output .= print_r($value, true);
    }
}

interface FileExistanceChecker
{
    public function isFile(string $file): bool;
}

class RealFileExistanceChecker implements FileExistanceChecker
{
    public function isFile(string $file): bool
    {
        return is_file($file);
    }
}

class StubFileExistanceChecker implements FileExistanceChecker
{
    /**
     * @var string[]
     */
    private array $files = [];

    /**
     * @param string[] $files
     */
    public function __construct(array $files = [])
    {
        $this->files = $files;
    }

    public function isFile(string $file): bool
    {
        return in_array($file, $this->files);
    }
}
