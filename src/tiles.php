<?php

declare(strict_types=1);

namespace Infoclimat\Tiles;

require_once __DIR__ . '/date.php';
require_once __DIR__ . '/io.php';

use Exception;
use PDO;

use function Infoclimat\Date\better_gmmktime;
use function Infoclimat\Date\DD_of;
use function Infoclimat\Date\hh_of;
use function Infoclimat\Date\ii_of;
use function Infoclimat\Date\MM_of;
use function Infoclimat\Date\YYYY_of;
use function Infoclimat\IO\connexion_sql;

/**
 * @param array{year: string|int, month: string|int, day: string|int, hour: string|int, minute: string|int} $date
 */
function transform_date_dictionnary_to_timestamp(array $date): int
{
    return better_gmmktime(
        (int) $date['year'],
        (int) $date['month'],
        (int) $date['day'],
        (int) $date['hour'],
        (int) $date['minute']
    );
}

function get_date_dictionary(int $timestamp): array
{
    return [
        'year'   => YYYY_of($timestamp),
        'month'  => MM_of($timestamp),
        'day'    => DD_of($timestamp),
        'hour'   => hh_of($timestamp),
        'minute' => ii_of($timestamp),
    ];
}

/**
 * @throws Exception
 */
function get_last_tiles_updates(): array
{
    $output = [];

    $lnk = connexion_sql('V5');
    $req = $lnk->query(
        <<<SQL
            SELECT *
            FROM V5.cartes_tuiles
            SQL
    );
    while ($rep = $req->fetch(PDO::FETCH_ASSOC)) {
        $output[$rep['nom']] = json_decode($rep['donnees'], true);
    }

    return $output;
}

/**
 * @throws Exception
 */
function get_last_tile_update(string $key): ?array
{
    $lnk = connexion_sql('V5');
    $req = $lnk->prepare(
        <<<SQL
            SELECT donnees
            FROM V5.cartes_tuiles
            WHERE nom = :nom
            LIMIT 1
            SQL
    );
    $req->execute(['nom' => $key]);
    $data = $req->fetchColumn();
    return $data ? json_decode($data, true) : null;
}

/**
 * @throws Exception
 */
function update_last_tile(string $key, array $last_datetime): void
{
    $lnk = connexion_sql('V5');
    $req = $lnk->prepare(
        <<<SQL
            INSERT INTO V5.cartes_tuiles(nom,  donnees)
            VALUES                      (:nom, :donnees)
            ON DUPLICATE KEY UPDATE donnees = VALUES(donnees)
            SQL
    );
    $req->execute([
        'nom'     => $key,
        'donnees' => json_encode($last_datetime),
    ]);
}

/**
 * @throws Exception
 */
function get_last_tiles_timestamps(): array
{
    $last_tiles_updates = get_last_tiles_updates();
    return array_map(fn($last_tile_update) => transform_date_dictionnary_to_timestamp($last_tile_update), $last_tiles_updates);
}

/**
 * @throws Exception
 */
function get_last_tile_timestamp(string $key): ?int
{
    $last_tile_update = get_last_tile_update($key);
    return $last_tile_update ? transform_date_dictionnary_to_timestamp($last_tile_update) : null;
}

/**
 * @throws Exception
 */
function update_last_tile_timestamp(string $key, int $timestamp): void
{
    $last_tile_update = get_date_dictionary($timestamp);
    update_last_tile($key, $last_tile_update);
}

interface LastTilesTimestampsRepository
{
    public function getLastTilesTimestamps(): array;

    public function getLastTileTimestamp(string $key): ?int;

    public function updateLastTileTimestamp(string $key, int $timestamp): void;
}

class RealLastTilesTimestampsRepository implements LastTilesTimestampsRepository
{
    /**
     * @throws Exception
     */
    public function getLastTilesTimestamps(): array
    {
        return get_last_tiles_timestamps();
    }

    /**
     * @throws Exception
     */
    public function getLastTileTimestamp(string $key): ?int
    {
        return get_last_tile_timestamp($key);
    }

    /**
     * @throws Exception
     */
    public function updateLastTileTimestamp(string $key, int $timestamp): void
    {
        update_last_tile_timestamp($key, $timestamp);
    }
}

class InMemoryLastTilesTimestampsRepository implements LastTilesTimestampsRepository
{
    /**
     * @var array[]
     */
    public array $timestamps = [];

    public function __construct(array $timestamps = [])
    {
        $this->timestamps = $timestamps;
    }

    public function getLastTilesTimestamps(): array
    {
        return $this->timestamps;
    }

    public function getLastTileTimestamp(string $key): ?int
    {
        return $this->timestamps[$key] ?? null;
    }

    public function updateLastTileTimestamp(string $key, int $timestamp): void
    {
        $this->timestamps[$key] = $timestamp;
    }
}
