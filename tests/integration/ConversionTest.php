<?php

declare(strict_types=1);

namespace Infoclimat\Radar\Conversion\Tests\Integration;

require_once __ROOT__ . '/conversion.php';
require_once __ROOT__ . '/io.php';

use Infoclimat\IO\RealCommandExecutor;
use Infoclimat\IO\RealFileExistanceChecker;
use Infoclimat\IO\RealOutputer;
use PHPUnit\Framework\TestCase;

use function Infoclimat\Radar\Conversion\color_tif;
use function Infoclimat\Radar\Conversion\convert_h5_to_tif;

final class ConversionTest extends TestCase
{
    public function testName(): void
    {
        $data = [];
        $expected = [];
        $this->assertSame($expected, $data);
        $this->assertNull(null);
        $this->assertSame('2000-06-15 12:30:00', '2000-06-15 12:30:00');
    }

    public function testConvertH5ToTif(): void
    {
        $test_dir = '/tmp/radar_conversion_test';
        if (!is_dir($test_dir)) {
            mkdir($test_dir, 0777, true);
        }
        $h5_file = __DIR__ . "/../data/mosaiques_MF_LAME_D_EAU_METROPOLE_21_v00.h5";
        $tif_file = "{$test_dir}/test.tif";

        $command_executor = new RealCommandExecutor();
        $file_existance_checker = new RealFileExistanceChecker();
        $outputer = new RealOutputer();

        convert_h5_to_tif(
            $h5_file,
            $tif_file,
            true,
            $command_executor,
            $file_existance_checker,
            $outputer
        );

        $this->assertTrue(file_exists($tif_file), 'TIF file should be created');

        convert_h5_to_tif(
            $h5_file,
            $tif_file,
            true,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertTrue(file_exists($tif_file), 'TIF file should be overwritten');
    }

    public function testColorTif(): void
    {
        $test_dir = '/tmp/radar_conversion_test';
        if (!is_dir($test_dir)) {
            mkdir($test_dir, 0777, true);
        }
        $tif_file = __DIR__ . "/../data/mosaiques_MF_LAME_D_EAU_METROPOLE_21_v00.tif";
        $colored_tif_file = "{$test_dir}/test_color.tif";

        $command_executor = new RealCommandExecutor();
        $file_existance_checker = new RealFileExistanceChecker();
        $outputer = new RealOutputer();

        color_tif(
            $tif_file,
            $colored_tif_file,
            true,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertTrue(file_exists($colored_tif_file), 'Colored TIF file should be created');

        color_tif(
            $tif_file,
            $colored_tif_file,
            true,
            $command_executor,
            $file_existance_checker,
            $outputer
        );
        $this->assertTrue(file_exists($colored_tif_file), 'Colored TIF file should be overwritten');
    }
}
