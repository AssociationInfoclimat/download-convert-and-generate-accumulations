<?php

declare(strict_types=1);

namespace Infoclimat\Radar\Tests\Unit;

require_once __ROOT__ . '/env.php';
require_once __ROOT__ . '/meteofrance-api.php';
require_once __ROOT__ . '/conversion.php';
require_once __ROOT__ . '/io.php';

use Infoclimat\IO\FakeCommandExecutor;
use Infoclimat\IO\FakeOutputer;
use Infoclimat\IO\StubFileExistanceChecker;
use Infoclimat\Tiles\InMemoryLastTilesTimestampsRepository;
use PHPUnit\Framework\TestCase;

use function Infoclimat\Radar\Conversion\color_tif;
use function Infoclimat\Radar\Conversion\compute_cumuls;
use function Infoclimat\Radar\Conversion\convert_h5_to_tif;
use function Infoclimat\Radar\Conversion\convert_hd5_to_colored_tif;
use function Infoclimat\Radar\Conversion\get_colored_tif_path;
use function Infoclimat\Radar\Conversion\get_h5_path;
use function Infoclimat\Radar\Conversion\get_tif_path;
use function Infoclimat\Radar\Conversion\get_tmp_ram_path;

use const Infoclimat\Env\TILES_PATH;

final class ConversionTest extends TestCase
{
    private string $palette_path;

    protected function setUp(): void
    {
        $this->palette_path = dirname(__DIR__, 2) . '/palettes/LAME_D_EAU_vers_RGBi.pal';
    }

    public function testGetTmpRamPath(): void
    {
        $this->assertSame('/dev/shm/filename.ext', get_tmp_ram_path('/disk/path/filename.ext'));
    }

    public function testGetH5Path(): void
    {
        $this->assertSame(
            TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5',
            get_h5_path('METROPOLE', strtotime('2000-06-15T12:30:45Z'))
        );
    }

    public function testGetTifPath(): void
    {
        $this->assertSame(
            TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif',
            get_tif_path('METROPOLE', strtotime('2000-06-15T12:30:45Z'))
        );
    }

    public function testGetColoredTifPath(): void
    {
        $this->assertSame(
            TILES_PATH . '/2000/06/15/radaric_MF_METROPOLE_12_v30.tif',
            get_colored_tif_path('METROPOLE', strtotime('2000-06-15T12:30:45Z'))
        );
    }

    public function testConvertH5ToTif_whenAlreadyExisting(): void
    {
        $h5_file_path = '/disk/path.h5';
        $tif_file_path = '/disk/path.tif';
        $replace_existing = false;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker(['/disk/path.tif']);
        $outputer = new FakeOutputer();
        convert_h5_to_tif(
            $h5_file_path,
            $tif_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertEmpty($command_executor->commands);
        $this->assertSame(
            <<<TXT
Skipping :
  - h5 /disk/path.h5
  - because tif /disk/path.tif
      already exists and replace mode is not active (--replace or --replace=true).

TXT,
            $outputer->output
        );
    }

    public function testConvertH5ToTif_whenReplacing(): void
    {
        $h5_file_path = '/disk/path.h5';
        $tif_file_path = '/disk/path.tif';
        $replace_existing = true;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker(['/disk/path.tif']);
        $outputer = new FakeOutputer();
        convert_h5_to_tif(
            $h5_file_path,
            $tif_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertSame(
            [
                'cp /disk/path.h5 /dev/shm/path.h5 2>&1',
                <<<SH
gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/path.h5"://dataset1/data1/data /dev/shm/path.tif 2>&1
SH,
                'mv /dev/shm/path.tif /disk/path.tif 2>&1',
            ],
            $command_executor->commands
        );
        $this->assertSame(
            <<<TXT
Replacing existing tif /disk/path.tif
Converting :
  - h5 /disk/path.h5
  - to tif /disk/path.tif
Running : cp /disk/path.h5 /dev/shm/path.h5 2>&1
Running : gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/path.h5"://dataset1/data1/data /dev/shm/path.tif 2>&1
Running : mv /dev/shm/path.tif /disk/path.tif 2>&1

TXT,
            $outputer->output
        );
    }

    public function testConvertH5ToTif(): void
    {
        $h5_file_path = '/disk/path.h5';
        $tif_file_path = '/disk/path.tif';
        $replace_existing = false;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker();
        $outputer = new FakeOutputer();
        convert_h5_to_tif(
            $h5_file_path,
            $tif_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertSame(
            [
                'cp /disk/path.h5 /dev/shm/path.h5 2>&1',
                <<<SH
gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/path.h5"://dataset1/data1/data /dev/shm/path.tif 2>&1
SH,
                'mv /dev/shm/path.tif /disk/path.tif 2>&1',
            ],
            $command_executor->commands
        );
        $this->assertSame(
            <<<TXT
Converting :
  - h5 /disk/path.h5
  - to tif /disk/path.tif
Running : cp /disk/path.h5 /dev/shm/path.h5 2>&1
Running : gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/path.h5"://dataset1/data1/data /dev/shm/path.tif 2>&1
Running : mv /dev/shm/path.tif /disk/path.tif 2>&1

TXT,
            $outputer->output
        );
    }

    public function testColorTif_whenAlreadyExisting(): void
    {
        $tif_file_path = '/disk/path.tif';
        $colored_file_path = '/disk/colored.tif';
        $replace_existing = false;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker(['/disk/colored.tif']);
        $outputer = new FakeOutputer();
        color_tif(
            $tif_file_path,
            $colored_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertEmpty($command_executor->commands);
        $this->assertSame(
            <<<TXT
Skipping :
  - tif /disk/path.tif
  - because colored tif /disk/colored.tif
      already exists and replace mode is not active (--replace or --replace=true).

TXT,
            $outputer->output
        );
    }

    public function testColorTif_whenReplacing(): void
    {
        $tif_file_path = '/disk/path.tif';
        $colored_file_path = '/disk/colored.tif';
        $replace_existing = true;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker(['/disk/colored.tif']);
        $outputer = new FakeOutputer();
        color_tif(
            $tif_file_path,
            $colored_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertSame(
            [
                'cp /disk/path.tif /dev/shm/path.tif 2>&1',
                <<<SH
gdaldem color-relief /dev/shm/path.tif {$this->palette_path} /dev/shm/colored.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1
SH,
                'mv /dev/shm/colored.tif /disk/colored.tif 2>&1',
            ],
            $command_executor->commands
        );
        $this->assertSame(
            <<<TXT
Replacing existing colored tif /disk/colored.tif
Converting :
  - tif /disk/path.tif
  - to colored tif /disk/colored.tif
Running : cp /disk/path.tif /dev/shm/path.tif 2>&1
Running : gdaldem color-relief /dev/shm/path.tif {$this->palette_path} /dev/shm/colored.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1
Running : mv /dev/shm/colored.tif /disk/colored.tif 2>&1

TXT,
            $outputer->output
        );
    }

    public function testColorTif(): void
    {
        $tif_file_path = '/disk/path.tif';
        $colored_file_path = '/disk/colored.tif';
        $replace_existing = false;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker();
        $outputer = new FakeOutputer();
        color_tif(
            $tif_file_path,
            $colored_file_path,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertSame(
            [
                'cp /disk/path.tif /dev/shm/path.tif 2>&1',
                "gdaldem color-relief /dev/shm/path.tif {$this->palette_path} /dev/shm/colored.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1",
                'mv /dev/shm/colored.tif /disk/colored.tif 2>&1',
            ],
            $command_executor->commands
        );
        $this->assertSame(
            <<<TXT
Converting :
  - tif /disk/path.tif
  - to colored tif /disk/colored.tif
Running : cp /disk/path.tif /dev/shm/path.tif 2>&1
Running : gdaldem color-relief /dev/shm/path.tif {$this->palette_path} /dev/shm/colored.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1
Running : mv /dev/shm/colored.tif /disk/colored.tif 2>&1

TXT,
            $outputer->output
        );
    }

    public function testComputeCumuls(): void
    {
        $zone = 'METROPOLE';
        $timestamp = 1234567890;
        $command_executor = new FakeCommandExecutor();
        $outputer = new FakeOutputer();
        compute_cumuls($zone, $timestamp, $command_executor, $outputer);
        $PYTHON_SCRIPT_PROJECT_PATH = dirname(__DIR__, 2) . '/generate-radaric-mf-values-accumulations';
        $this->assertSame(
            [
                "cd {$PYTHON_SCRIPT_PROJECT_PATH} && poetry run python ./generate_radaric_mf_values_accumulations/main.py --timestamp 1234567890 --zone METROPOLE 2>&1",
            ],
            $command_executor->commands
        );
        $this->assertSame(
            <<<TXT
Running : cd {$PYTHON_SCRIPT_PROJECT_PATH} && poetry run python ./generate_radaric_mf_values_accumulations/main.py --timestamp 1234567890 --zone METROPOLE 2>&1

TXT,
            $outputer->output
        );

    }

    public function testConvertHd5ToColoredTif(): void
    {
        $zone = 'METROPOLE';
        $timestamp = strtotime('2000-06-15T12:30:00Z');
        $replace_existing = false;
        $command_executor = new FakeCommandExecutor();
        $file_existance_checker = new StubFileExistanceChecker([TILES_PATH . '/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5']);
        $last_tiles_timestamp_repository = new InMemoryLastTilesTimestampsRepository();
        $outputer = new FakeOutputer();
        convert_hd5_to_colored_tif(
            $zone,
            $timestamp,
            $replace_existing,
            $command_executor,
            $file_existance_checker,
            $last_tiles_timestamp_repository,
            $outputer
        );
        $TILES_PATH = TILES_PATH;
        $this->assertSame(
            [
                "cp {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5 /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5 2>&1",
                <<<SH
gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5"://dataset1/data1/data /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1
SH,
                "mv /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1",
                "cp {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1",
                "gdaldem color-relief /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif {$this->palette_path} /dev/shm/radaric_MF_METROPOLE_12_v30.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1",
                "mv /dev/shm/radaric_MF_METROPOLE_12_v30.tif {$TILES_PATH}/2000/06/15/radaric_MF_METROPOLE_12_v30.tif 2>&1",
            ],
            $command_executor->commands
        );
        $this->assertSame(
            ['radaric_MF_METROPOLE' => strtotime('2000-06-15T12:30:00Z')],
            $last_tiles_timestamp_repository->getLastTilesTimestamps()
        );
        $this->assertSame(
            <<<TXT
Converting :
  - h5 {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5
  - to tif {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif
Running : cp /media/datastore/tempsreel.infoclimat.net/tiles/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5 /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5 2>&1
Running : gdalwarp -t_srs EPSG:3857 -tr 300 300 -r lanczos -srcnodata 65535 -co 'COMPRESS=LZW' -co 'PREDICTOR=YES' -of COG -overwrite HDF5:"/dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.h5"://dataset1/data1/data /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1
Running : mv /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif /media/datastore/tempsreel.infoclimat.net/tiles/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1
Converting :
  - tif {$TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif
  - to colored tif {$TILES_PATH}/2000/06/15/radaric_MF_METROPOLE_12_v30.tif
Running : cp /media/datastore/tempsreel.infoclimat.net/tiles/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif 2>&1
Running : gdaldem color-relief /dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif {$this->palette_path} /dev/shm/radaric_MF_METROPOLE_12_v30.tif -alpha -nearest_color_entry -co 'COMPRESS=JPEG' -co 'PREDICTOR=YES' -of COG 2>&1
Running : mv /dev/shm/radaric_MF_METROPOLE_12_v30.tif /media/datastore/tempsreel.infoclimat.net/tiles/2000/06/15/radaric_MF_METROPOLE_12_v30.tif 2>&1

TXT,
            $outputer->output
        );
    }

    public function testName(): void
    {
        $data = [];
        $expected = [];
        $this->assertSame($expected, $data);
        $this->assertNull(null);
        $this->assertSame('2000-06-15 12:30:00', '2000-06-15 12:30:00');
    }
}
